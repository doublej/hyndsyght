import sqlite3

from hyndsyght.store.events import (
    open_or_close_agent_event,
    update_interval_end,
    write_interval,
)


def test_write_interval_inserts_row(conn: sqlite3.Connection) -> None:
    row_id = write_interval(
        conn, source="window", kind="app", title="Terminal", ts_start=1.0, ts_end=2.0
    )
    row = conn.execute(
        "SELECT source, kind, title, ts_start, ts_end FROM raw_events WHERE id = ?",
        (row_id,),
    ).fetchone()
    assert row == ("window", "app", "Terminal", 1.0, 2.0)


def test_update_interval_end_updates_only_ts_end(conn: sqlite3.Connection) -> None:
    row_id = write_interval(
        conn, source="afk", kind="active", title=None, ts_start=1.0, ts_end=None
    )
    update_interval_end(conn, row_id, 5.0)
    assert (
        conn.execute(
            "SELECT ts_end FROM raw_events WHERE id = ?", (row_id,)
        ).fetchone()[0]
        == 5.0
    )


def test_agent_event_open_is_idempotent(conn: sqlite3.Connection) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=1.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    open_or_close_agent_event(
        conn,
        event_uid="turn:1",
        ts=1.0,
        kind="claude-code-turn",
        title=None,
        payload=None,
        closing=False,
    )
    rows = conn.execute(
        "SELECT ts_start, ts_end FROM raw_events WHERE event_uid = 'turn:1'"
    ).fetchall()
    assert rows == [(1.0, None)]


def test_agent_event_close_is_idempotent_and_only_closes_open_rows(
    conn: sqlite3.Connection,
) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:2",
        ts=1.0,
        kind="claude-code-turn",
        title="in progress",
        payload=None,
        closing=False,
    )
    for _ in range(2):
        open_or_close_agent_event(
            conn,
            event_uid="turn:2",
            ts=9.0,
            kind="claude-code-turn",
            title="done",
            payload={"a": 1},
            closing=True,
        )
    rows = conn.execute(
        "SELECT ts_start, ts_end, title FROM raw_events WHERE event_uid = 'turn:2'"
    ).fetchall()
    # title is set once at open; close only ever touches ts_end/payload, per spec.
    assert rows == [(1.0, 9.0, "in progress")]


def test_a_close_with_no_matching_open_inserts_nothing(
    conn: sqlite3.Connection,
) -> None:
    open_or_close_agent_event(
        conn,
        event_uid="turn:never-opened",
        ts=9.0,
        kind="claude-code-turn",
        title=None,
        payload={"last_assistant_message": "done"},
        closing=True,
    )
    assert conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0] == 0
