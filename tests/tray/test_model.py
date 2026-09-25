import json
import sqlite3
import time
from pathlib import Path

import pytest

from hyndsyght.categorize import rules
from hyndsyght.tray import model
from hyndsyght.tray.model import Snapshot, format_duration, menu_items

NOW = 1_000_000.0


def snap(**overrides: object) -> Snapshot:
    base = {
        "today_seconds": 3 * 3600 + 12 * 60,
        "activity": "Code · hyndsyght — cli.py",
        "daemon_running": True,
        "permission_off": False,
        "paused_until": 0.0,
    }
    return Snapshot(**{**base, **overrides})  # type: ignore[arg-type]


def labels(snapshot: Snapshot) -> list[str]:
    return [item.label for item in menu_items(snapshot, "en", NOW)]


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0, "0m"),
        (59, "0m"),
        (60, "1m"),
        (3 * 3600 + 12 * 60, "3h 12m"),
        (12 * 3600 + 5 * 60, "12h 5m"),
    ],
)
def test_format_duration(seconds: float, text: str) -> None:
    assert format_duration(seconds) == text


def test_menu_in_the_normal_state() -> None:
    assert labels(snap()) == [
        "Today: 3h 12m",
        "Now: Code · hyndsyght — cli.py",
        "-",
        "Open dashboard",
        "Pause tracking",
        "Restart daemon",
        "-",
        "Quit hyndsyght",
    ]
    pause = menu_items(snap(), "en", NOW)[4]
    assert [c.action for c in pause.children] == [
        "pause_15m",
        "pause_1h",
        "pause_forever",
    ]


def test_menu_when_idle() -> None:
    assert labels(snap(activity=None))[1] == "Now: Idle"


def test_menu_when_paused_swaps_pause_for_resume() -> None:
    until = NOW + 900
    names = labels(snap(paused_until=until))
    assert names[1] == f"Paused until {time.strftime('%H:%M', time.localtime(until))}"
    assert "Resume tracking" in names and "Pause tracking" not in names
    assert labels(snap(paused_until=float("inf")))[1] == "Paused until you resume"


def test_menu_when_the_daemon_is_down() -> None:
    assert labels(snap(daemon_running=False))[2] == "⚠ Daemon is not running"
    assert (
        model.icon_name(daemon_running=False, paused=True) == "exclamationmark.triangle"
    )


def test_menu_when_the_permission_is_off() -> None:
    item = menu_items(snap(permission_off=True), "en", NOW)[2]
    assert (item.label, item.action) == (
        "⚠ Screen Recording looks off",
        "open_permission",
    )


def test_menu_speaks_dutch() -> None:
    assert menu_items(snap(), "nl", NOW)[0].label == "Vandaag: 3h 12m"


def _window(
    conn: sqlite3.Connection, title: str, app: str, start: float, end: float
) -> None:
    conn.execute(
        "INSERT INTO raw_events (source, kind, title, ts_start, ts_end, payload,"
        " created_at) VALUES ('window', 'window', ?, ?, ?, ?, ?)",
        (title, start, end, json.dumps({"app": app}), start),
    )
    conn.commit()


def test_snapshot_reads_today_and_the_current_window(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    rules.ensure_default()
    now = time.mktime((*time.localtime()[:3], 12, 0, 0, 0, 0, -1))  # today, noon
    _window(conn, "hyndsyght — cli.py", "Code", now - 600, now - 10)
    result = model.snapshot(now)
    assert result.activity == "Code · hyndsyght — cli.py"
    assert result.today_seconds == pytest.approx(590)
    assert result.paused_until == 0.0


def test_snapshot_is_idle_when_the_window_row_went_stale(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    now = time.time()
    _window(conn, "Inbox", "Mail", now - 600, now - 120)
    assert model.current_activity(now) is None


def test_activity_is_cut_at_50_chars(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    now = time.time()
    _window(conn, "x" * 80, "Code", now - 30, now)
    activity = model.current_activity(now)
    assert activity is not None and len(activity) == 50 and activity.endswith("…")
