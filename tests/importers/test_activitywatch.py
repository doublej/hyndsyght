"""The ActivityWatch importer, against a small made-up export."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from hyndsyght.categorize.rules import TEMPLATE
from hyndsyght.cli import main
from hyndsyght.importers import activitywatch as aw
from hyndsyght.platform.types import Event
from hyndsyght.store.db import connect, init_db
from hyndsyght.store.events import write_interval

T0 = datetime(2026, 3, 2, 9, tzinfo=UTC).timestamp()
WINDOW = "aw-watcher-window_desk.local"
AFK = "aw-watcher-afk_desk.local"


def _aw(event_id: int, offset: float, duration: float, **data: Any) -> dict[str, Any]:
    stamp = datetime.fromtimestamp(T0 + offset, UTC).isoformat().replace("+00:00", "Z")
    return {"id": event_id, "timestamp": stamp, "duration": duration, "data": data}


def _bucket(
    client: str, events: list[dict[str, Any]], host: str = "desk.local"
) -> dict[str, Any]:
    return {
        "client": client,
        "hostname": host,
        "created": "2026-03-01T00:00:00Z",
        "events": events[::-1],
    }  # aw-server exports newest first


EXPORT = {
    "buckets": {
        WINDOW: _bucket(
            "aw-watcher-window",
            [
                _aw(1, 0, 10, app="iTerm2", title="✳ quiet-otter"),
                _aw(2, 10, 10, app="iTerm2", title="✳ quiet-otter"),
                _aw(
                    3, 20, 1, app="Slack", title="Slack | Acme"
                ),  # a blip: folds into iTerm2
                _aw(4, 21, 19, app="iTerm2", title="✳ quiet-otter"),
                _aw(5, 40, 60, app="1Password", title="Globex vault"),
                _aw(
                    6, 100, 300, app="loginwindow", title="loginwindow"
                ),  # away: dropped
                _aw(7, 400, 3600, app="Google Chrome", title="Globex board"),
            ],
        ),
        AFK: _bucket(
            "aw-watcher-afk",
            [
                _aw(10, 0, 100, status="not-afk"),
                _aw(11, 100, 300, status="afk"),
                _aw(12, 400, 3600, status="not-afk"),
            ],
        ),
        "aw-watcher-window_agents": _bucket(
            "aw-watcher-agents", [_aw(20, 0, 60, app="x")]
        ),
        "aw-import-screentime_desk.local": _bucket("aw-import-screentime", []),
        "aw-watcher-window_laptop.local": _bucket(
            "aw-watcher-window", [], host="laptop.local"
        ),
    }
}


@pytest.fixture
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db(tmp_path / "hyndsyght.db")
    (tmp_path / "rules.toml").write_text(TEMPLATE)
    (tmp_path / "export.json").write_text(json.dumps(EXPORT))
    return tmp_path


def _import(state: Path, *args: str) -> str:
    result = CliRunner().invoke(
        main,
        [
            "--lang",
            "en",
            "import",
            "activitywatch",
            "--file",
            str(state / "export.json"),
            *args,
        ],
    )
    assert result.exit_code == 0, result.output
    return result.output


def _rows(state: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(state / "hyndsyght.db")
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM raw_events WHERE source = 'window' ORDER BY ts_start"
    ).fetchall()


def test_import_merges_folds_redacts_and_drops_away(state: Path) -> None:
    _import(state)
    rows = [(r["ts_start"] - T0, r["ts_end"] - T0, r["title"]) for r in _rows(state)]
    assert rows == [
        (0, 40, "✳ quiet-otter"),  # four events, one with a 1 s blip, one row
        (40, 100, None),  # 1Password: the time stays, the title never lands
        (400, 4000, "Globex board"),
    ]
    payload = json.loads(_rows(state)[1]["payload"])
    assert payload == {
        "app": "1Password",
        "imported": "activitywatch",
        "redacted": True,
    }


def test_afk_status_becomes_active_and_afk_rows(state: Path) -> None:
    _import(state)
    conn = sqlite3.connect(state / "hyndsyght.db")
    kinds = conn.execute(
        "SELECT kind, ts_start - ?, ts_end - ? FROM raw_events WHERE source = 'afk' ORDER BY ts_start",
        (T0, T0),
    ).fetchall()
    assert kinds == [("active", 0, 100), ("afk", 100, 400), ("active", 400, 4000)]


def test_import_stops_where_native_recording_begins(state: Path) -> None:
    conn = connect(state / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="window",
            title="native",
            ts_start=T0 + 1000,
            ts_end=T0 + 1100,
            payload={"app": "Mail"},
        )
    output = _import(state)
    chrome = [r for r in _rows(state) if r["title"] == "Globex board"]
    assert [(r["ts_start"] - T0, r["ts_end"] - T0) for r in chrome] == [(400, 1000)]
    assert "Stopped at" in output


def test_running_it_again_replaces_and_undo_leaves_native_rows(state: Path) -> None:
    conn = connect(state / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="window",
            title="native",
            ts_start=T0 + 9000,
            ts_end=T0 + 9100,
            payload={"app": "Mail"},
        )
    _import(state)
    first = len(_rows(state))
    _import(state)
    assert len(_rows(state)) == first == 4
    result = CliRunner().invoke(
        main, ["--lang", "en", "import", "activitywatch", "--undo"]
    )
    assert "Removed 6 rows" in result.output  # 3 window rows + 3 afk rows
    assert [r["title"] for r in _rows(state)] == ["native"]


def test_dry_run_writes_nothing_and_reports_per_bucket(state: Path) -> None:
    output = _import(state, "--dry-run")
    assert _rows(state) == []
    assert (
        f"{WINDOW}: 3 rows, 2026-03-02 to 2026-03-02. 1 with a hidden title." in output
    )
    assert f"{AFK}: 3 rows" in output
    assert "agents" not in output and "screentime" not in output
    assert "Dry run: 6 rows would be imported. Nothing was written." in output


def test_host_limits_the_buckets(state: Path) -> None:
    output = _import(state, "--host", "laptop.local", "--dry-run")
    assert (
        output.splitlines()[0] == "aw-watcher-window_laptop.local: nothing to import."
    )


def test_overlapping_events_do_not_overlap_as_rows() -> None:
    a, b = Event("window", "A", {"app": "A"}), Event("window", "B", {"app": "B"})
    runs = list(aw.merge("w", [(0, 30, "1", a), (20, 50, "2", b)]))
    assert [(r.start, r.end, r.event.title) for r in runs] == [
        (0, 20, "A"),
        (20, 50, "B"),
    ]


def test_api_pages_monthly_from_the_first_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    source = aw.ApiSource("http://aw.test/")
    monkeypatch.setattr(
        source, "_get", lambda path, **params: calls.append(params) or []
    )
    bucket = {
        "created": "2026-03-01T02:00:00Z",
        "metadata": {"start": "2026-03-01T00:00:00Z"},
    }
    first = datetime(2026, 3, 1, tzinfo=UTC).timestamp()
    list(source.events(WINDOW, bucket, until=first + 45 * 86400))
    assert [c["start"][:10] for c in calls] == ["2026-03-01", "2026-03-31"]
    assert calls[0]["start"].startswith("2026-03-01T00:00:00")  # not `created`


def test_unreachable_server_is_a_plain_error(state: Path) -> None:
    result = CliRunner().invoke(
        main, ["--lang", "en", "import", "activitywatch", "--url", "http://127.0.0.1:9"]
    )
    assert result.exit_code == 1
    assert "Can't reach ActivityWatch at http://127.0.0.1:9" in result.output
