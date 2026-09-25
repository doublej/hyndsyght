"""Repair paths: backfill_agent_cwd, the SessionEnd cap, and delete_unmatched_closes.

Split from test_ingest.py to stay under the file-length cap (.quality.json).
"""

import json
import sqlite3
from pathlib import Path

from hyndsyght.agentwatch.ingest import (
    backfill_agent_cwd,
    delete_unmatched_closes,
    ingest,
)
from hyndsyght.agentwatch.reaper import REAP_TIMEOUT_SECONDS


def _write(spool_path: Path, *payloads: dict) -> None:
    with spool_path.open("a") as f:
        for payload in payloads:
            f.write(json.dumps(payload) + "\n")


def _payload(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT payload FROM raw_events WHERE source = 'agent'"
    ).fetchone()
    return json.loads(row[0])


def test_backfill_restores_the_project_from_the_spool(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "prompt_id": "p1",
            "cwd": "/work/demo",
            "_received_at": 1.0,
        },
    )
    ingest(conn, spool_path)
    # simulate the old destructive close
    conn.execute('UPDATE raw_events SET payload = \'{"intent": "x"}\'')
    assert backfill_agent_cwd(conn, spool_path) == 1
    payload = _payload(conn)
    assert payload["cwd"] == "/work/demo"
    assert payload["intent"] == "x"


def test_backfill_is_idempotent(conn: sqlite3.Connection, tmp_path: Path) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "prompt_id": "p1",
            "cwd": "/work/demo",
            "_received_at": 1.0,
        },
    )
    ingest(conn, spool_path)
    conn.execute("UPDATE raw_events SET payload = '{}'")
    assert backfill_agent_cwd(conn, spool_path) == 1
    assert backfill_agent_cwd(conn, spool_path) == 0


def test_backfill_leaves_sessions_the_spool_never_saw(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "unknown",
            "prompt_id": "p1",
            "_received_at": 1.0,
        },
    )
    ingest(conn, spool_path)
    conn.execute("UPDATE raw_events SET payload = '{}'")
    assert backfill_agent_cwd(conn, spool_path) == 0


def test_subagent_open_stores_cwd(conn: sqlite3.Connection, tmp_path: Path) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "SubagentStart",
            "session_id": "s1",
            "agent_id": "a1",
            "cwd": "/work/demo",
            "_received_at": 1.0,
        },
    )
    ingest(conn, spool_path)
    assert _payload(conn)["cwd"] == "/work/demo"


def test_session_end_sweep_caps_a_row_open_past_the_timeout(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "prompt_id": "p1",
            "_received_at": 1.0,
        },
        {
            "hook_event_name": "SessionEnd",
            "session_id": "s1",
            "_received_at": 1.0 + REAP_TIMEOUT_SECONDS * 100,
        },
    )
    ingest(conn, spool_path)
    rows = conn.execute(
        "SELECT ts_end FROM raw_events WHERE source = 'agent'"
    ).fetchall()
    assert rows == [(1.0 + REAP_TIMEOUT_SECONDS,)]


def _insert_legacy_phantom_row(conn: sqlite3.Connection) -> None:
    """A row the pre-fix store/events.py inserted for an unmatched close:
    ts_start at the close's time, no session_id in its payload (only what a
    close merges in), title from the close call.
    """
    conn.execute(
        "INSERT INTO raw_events "
        "(event_uid, ts_start, ts_end, source, kind, title, payload, created_at) "
        "VALUES ('agent-subagent:s1:a1', 9.0, NULL, 'agent', 'claude-code-subagent',"
        " 'recon', '{\"last_assistant_message\": \"done\"}', 9.0)"
    )
    conn.commit()


def test_delete_unmatched_closes_removes_a_close_with_no_open(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _insert_legacy_phantom_row(conn)
    spool_path = tmp_path / "spool.jsonl"  # empty: no SubagentStart was ever spooled

    assert delete_unmatched_closes(conn, spool_path) == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0] == 0


def test_delete_unmatched_closes_keeps_rows_that_really_opened(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "SubagentStart",
            "session_id": "s1",
            "agent_id": "a1",
            "agent_type": "recon",
            "_received_at": 1.0,
        },
        {
            "hook_event_name": "SubagentStop",
            "session_id": "s1",
            "agent_id": "a1",
            "agent_type": "recon",
            "last_assistant_message": "done",
            "_received_at": 9.0,
        },
    )
    ingest(conn, spool_path)
    assert delete_unmatched_closes(conn, spool_path) == 0
    assert conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0] == 1


def test_delete_unmatched_closes_is_idempotent(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _insert_legacy_phantom_row(conn)
    spool_path = tmp_path / "spool.jsonl"

    assert delete_unmatched_closes(conn, spool_path) == 1
    assert delete_unmatched_closes(conn, spool_path) == 0
