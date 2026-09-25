import json
import sqlite3
from pathlib import Path

from hyndsyght.agentwatch.ingest import ingest


def _write(spool_path: Path, *payloads: dict) -> None:
    with spool_path.open("a") as f:
        for payload in payloads:
            f.write(json.dumps(payload) + "\n")


def test_user_prompt_submit_then_stop_closes_the_same_turn(
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
    )
    ingest(conn, spool_path)
    _write(
        spool_path,
        {
            "hook_event_name": "Stop",
            "session_id": "s1",
            "prompt_id": "p1",
            "_received_at": 9.0,
            "last_assistant_message": "done",
            "stop_reason": "end_turn",
        },
    )
    ingest(conn, spool_path)

    rows = conn.execute(
        "SELECT ts_start, ts_end, kind FROM raw_events WHERE source = 'agent'"
    ).fetchall()
    assert rows == [(1.0, 9.0, "claude-code-turn")]


def test_closing_a_turn_stores_a_derived_intent(
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
            "hook_event_name": "Stop",
            "session_id": "s1",
            "prompt_id": "p1",
            "_received_at": 9.0,
            "last_assistant_message": "Fixed the bug. Also ran the tests.",
            "stop_reason": "end_turn",
        },
    )
    ingest(conn, spool_path)

    (payload_json,) = conn.execute(
        "SELECT payload FROM raw_events WHERE source = 'agent'"
    ).fetchone()
    assert json.loads(payload_json)["intent"] == "Fixed the bug."


def test_stop_without_prompt_id_closes_the_open_turn(
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
    )
    ingest(conn, spool_path)
    _write(
        spool_path,
        {
            "hook_event_name": "Stop",
            "session_id": "s1",
            "_received_at": 9.0,
            "last_assistant_message": "done",
        },
    )
    ingest(conn, spool_path)

    rows = conn.execute(
        "SELECT ts_start, ts_end, event_uid FROM raw_events WHERE source = 'agent'"
    ).fetchall()
    assert rows == [(1.0, 9.0, "agent-turn:s1:p1")]


def test_malformed_line_is_skipped_not_raised(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    spool_path = tmp_path / "spool.jsonl"
    with spool_path.open("a") as f:
        f.write("not json\n")
        f.write(
            json.dumps(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "s1",
                    "prompt_id": "p1",
                    "_received_at": 1.0,
                }
            )
            + "\n"
        )

    ingest(conn, spool_path)

    rows = conn.execute("SELECT ts_start FROM raw_events").fetchall()
    assert rows == [(1.0,)]


def test_session_end_sweeps_dangling_open_rows(
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
            "hook_event_name": "SubagentStart",
            "session_id": "s1",
            "agent_id": "a1",
            "_received_at": 2.0,
        },
        {"hook_event_name": "SessionEnd", "session_id": "s1", "_received_at": 20.0},
    )
    ingest(conn, spool_path)

    rows = conn.execute(
        "SELECT ts_end FROM raw_events WHERE source = 'agent' ORDER BY ts_start"
    ).fetchall()
    assert rows == [(20.0,), (20.0,)]


def test_reingesting_same_lines_is_a_noop(
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
    )
    ingest(conn, spool_path)
    ingest(conn, spool_path)  # offset already advanced — no lines to reprocess

    rows = conn.execute("SELECT COUNT(*) FROM raw_events").fetchall()
    assert rows == [(1,)]


def _payload(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT payload FROM raw_events WHERE source = 'agent'"
    ).fetchone()
    return json.loads(row[0])


def test_closing_a_turn_keeps_the_project_it_was_opened_with(
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
        {
            "hook_event_name": "Stop",
            "session_id": "s1",
            "prompt_id": "p1",
            "last_assistant_message": "done",
            "_received_at": 9.0,
        },
    )
    ingest(conn, spool_path)
    payload = _payload(conn)
    assert payload["cwd"] == "/work/demo"
    assert payload["session_id"] == "s1"
    assert payload["last_assistant_message"] == "done"


def test_turn_without_prompt_id_opens_closes_and_keeps_the_project(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    spool_path = tmp_path / "spool.jsonl"
    _write(
        spool_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "cwd": "/work/demo",
            "_received_at": 1.0,
        },
        {
            "hook_event_name": "Stop",
            "session_id": "s1",
            "last_assistant_message": "done",
            "_received_at": 9.0,
        },
    )
    ingest(conn, spool_path)
    rows = conn.execute(
        "SELECT ts_start, ts_end, event_uid FROM raw_events WHERE source = 'agent'"
    ).fetchall()
    assert rows == [(1.0, 9.0, "agent-turn:s1:1.0")]
    payload = _payload(conn)
    assert payload["cwd"] == "/work/demo"
    assert payload["last_assistant_message"] == "done"
