import sqlite3

from hyndsyght.agentwatch.reaper import (
    REAP_TIMEOUT_SECONDS,
    reap,
    recap_reaped_durations,
)
from hyndsyght.store.events import open_or_close_agent_event


def test_reap_closes_stale_open_rows_at_the_cap_not_now(
    conn: sqlite3.Connection,
) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=0.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    closed = reap(conn, now=REAP_TIMEOUT_SECONDS + 999_999.0)
    assert closed == 1
    assert (
        conn.execute("SELECT ts_end FROM raw_events").fetchone()[0]
        == REAP_TIMEOUT_SECONDS
    )


def test_reap_leaves_recent_open_rows_alone(conn: sqlite3.Connection) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=0.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    closed = reap(conn, now=REAP_TIMEOUT_SECONDS - 1.0)
    assert closed == 0


def test_recap_caps_a_row_the_old_reaper_left_open_for_days(
    conn: sqlite3.Connection,
) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=0.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    # simulate the old buggy reaper: ts_end = now, no payload touch
    conn.execute("UPDATE raw_events SET ts_end = ?", (REAP_TIMEOUT_SECONDS * 100,))
    assert recap_reaped_durations(conn) == 1
    assert (
        conn.execute("SELECT ts_end FROM raw_events").fetchone()[0]
        == REAP_TIMEOUT_SECONDS
    )


def test_recap_leaves_a_genuine_long_close_alone(conn: sqlite3.Connection) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=0.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=REAP_TIMEOUT_SECONDS * 100,
        kind="claude-code-turn",
        title=None,
        payload={"last_assistant_message": "done", "stop_reason": "end_turn"},
        closing=True,
    )
    assert recap_reaped_durations(conn) == 0
    assert (
        conn.execute("SELECT ts_end FROM raw_events").fetchone()[0]
        == REAP_TIMEOUT_SECONDS * 100
    )


def test_recap_is_idempotent(conn: sqlite3.Connection) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=0.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    conn.execute("UPDATE raw_events SET ts_end = ?", (REAP_TIMEOUT_SECONDS * 100,))
    assert recap_reaped_durations(conn) == 1
    assert recap_reaped_durations(conn) == 0
