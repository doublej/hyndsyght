import time
from datetime import datetime
from pathlib import Path

from hyndsyght.mcpserver.server import (
    get_attention_summary,
    get_ledger_summary,
    list_recent_events,
)
from hyndsyght.store.db import connect, init_db
from hyndsyght.store.events import write_interval


def _init(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db()


def test_list_recent_events_redacts_titles_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    _init(tmp_path, monkeypatch)
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Secret Doc",
            ts_start=time.time(),
            ts_end=time.time(),
        )
    conn.close()

    rows = list_recent_events()
    assert len(rows) == 1
    assert rows[0]["title"] is None


def test_list_recent_events_can_opt_out_of_redaction(
    tmp_path: Path, monkeypatch
) -> None:
    _init(tmp_path, monkeypatch)
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Secret Doc",
            ts_start=time.time(),
            ts_end=time.time(),
        )
    conn.close()

    rows = list_recent_events(redact=False)
    assert rows[0]["title"] == "Secret Doc"


def test_list_recent_events_limit_is_respected(tmp_path: Path, monkeypatch) -> None:
    _init(tmp_path, monkeypatch)
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        for i in range(3):
            write_interval(
                conn,
                source="window",
                kind="app",
                title=f"App {i}",
                ts_start=time.time(),
                ts_end=time.time(),
            )
    conn.close()

    assert len(list_recent_events(limit=1)) == 1
    assert (
        len(list_recent_events(limit=999999)) == 3
    )  # capped internally, doesn't error


def test_source_filter_is_parameterized_not_string_concatenated(
    tmp_path: Path, monkeypatch
) -> None:
    _init(tmp_path, monkeypatch)
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Editor",
            ts_start=time.time(),
            ts_end=time.time(),
        )
    conn.close()

    injected = list_recent_events(source="window'; DROP TABLE raw_events; --")
    assert injected == []
    assert list_recent_events(source="window") != []


def test_attention_and_ledger_summaries_for_a_given_day(
    tmp_path: Path, monkeypatch
) -> None:
    _init(tmp_path, monkeypatch)
    day_start = datetime(2024, 1, 15).astimezone().timestamp()  # DST-aware midnight
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Editor",
            ts_start=day_start,
            ts_end=day_start + 600,
        )
        write_interval(
            conn,
            source="agent",
            kind="claude-code-turn",
            title=None,
            ts_start=day_start,
            ts_end=day_start + 600,
        )
    conn.close()

    attention = get_attention_summary("2024-01-15")
    assert attention["longest_stretch_seconds"] == 600.0

    ledger = get_ledger_summary("2024-01-15")
    assert ledger["human_minutes"] == 10.0
    assert ledger["agent_minutes"] == 10.0
    assert ledger["overlap_minutes"] == 10.0


def test_attention_and_ledger_summaries_clip_to_afk_active_spans(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression for hyndsyght-1uy: both tools must agree with /api/ledger,
    which reads active_window_rows (AFK-clipped), not raw window rows.
    """
    _init(tmp_path, monkeypatch)
    day_start = datetime(2024, 1, 15).astimezone().timestamp()
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Editor",
            ts_start=day_start,
            ts_end=day_start + 600,
        )
        # only the second half of the window row falls inside an active span —
        # the first half was AFK and must be clipped away.
        write_interval(
            conn,
            source="afk",
            kind="active",
            title=None,
            ts_start=day_start + 300,
            ts_end=day_start + 600,
        )
    conn.close()

    attention = get_attention_summary("2024-01-15")
    assert attention["longest_stretch_seconds"] == 300.0

    ledger = get_ledger_summary("2024-01-15")
    assert ledger["human_minutes"] == 5.0
