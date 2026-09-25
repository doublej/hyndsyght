"""Interprets spooled hook payloads into open/close writes on raw_events.

event_uid is keyed on (session_id, prompt_id) / (session_id, agent_id) —
the Phase 4 spike's primary scheme, per the documented hook payload shape
(prompt_id is a common field on every event). If prompt_id later proves
unstable across a UserPromptSubmit/Stop pair, switch to
f"agent-turn:{session_id}:{ts_start}" instead (closed only by the
SessionEnd sweep / reaper, no upsert-close matching needed).
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from hyndsyght import paths
from hyndsyght.agentwatch import spool
from hyndsyght.agentwatch.intent import extract_intent
from hyndsyght.agentwatch.reaper import REAP_TIMEOUT_SECONDS
from hyndsyght.store.events import open_or_close_agent_event, session_id_from_uid

INTENT_TRUNCATE_CHARS = (
    500  # ponytail: fixed truncation, revisit if Phase 8 needs more.
)


def ingest(conn: sqlite3.Connection, spool_path: Path | None = None) -> None:
    path = spool_path or paths.spool_path()
    lines, new_offset = spool.read_new_lines(path)
    with conn:
        for line in lines:
            _apply(conn, line)
    spool.write_offset(path, new_offset)


def backfill_agent_cwd(conn: sqlite3.Connection, spool_path: Path | None = None) -> int:
    """Restore session_id and cwd onto agent rows whose close overwrote them.

    Closing an event used to replace its whole payload rather than merge into
    it, so every closed turn lost the project it belonged to. The spool still
    holds every raw hook payload, so the mapping is recoverable. Idempotent:
    rows that already carry a cwd are skipped.
    """
    cwds = _session_cwds(spool_path or paths.spool_path())
    rows = conn.execute(
        "SELECT id, event_uid FROM raw_events "
        "WHERE source = 'agent' AND json_extract(payload, '$.cwd') IS NULL"
    ).fetchall()
    patches = [
        (json.dumps({"session_id": sid, "cwd": cwds[sid]}), row_id)
        for row_id, event_uid in rows
        if (sid := session_id_from_uid(event_uid)) in cwds
    ]
    with conn:
        conn.executemany(
            "UPDATE raw_events SET payload = json_patch(COALESCE(payload, '{}'), ?) "
            "WHERE id = ?",
            patches,
        )
    return len(patches)


def _session_cwds(spool_path: Path) -> dict[str, str]:
    """session_id -> cwd, read from the raw hook spool."""
    cwds: dict[str, str] = {}
    if not spool_path.exists():
        return cwds
    with spool_path.open(errors="replace") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            session_id, cwd = event.get("session_id"), event.get("cwd")
            if session_id and cwd:
                cwds.setdefault(session_id, cwd)
    return cwds


def delete_unmatched_closes(
    conn: sqlite3.Connection, spool_path: Path | None = None
) -> int:
    """Remove agent rows a close with no matching open created.

    store/events.py used to insert a fresh open row for a Stop/SubagentStop
    with nothing to close, which the reaper then turned into a phantom
    ~45-minute row. The spool is the source of truth for whether a real open
    ever happened: a row whose event_uid has no matching
    UserPromptSubmit/SubagentStart there was never really open. Idempotent:
    already-removed rows stay removed.
    """
    opened = _opened_event_uids(spool_path or paths.spool_path())
    rows = conn.execute(
        "SELECT id, event_uid FROM raw_events "
        "WHERE source = 'agent' AND event_uid IS NOT NULL"
    ).fetchall()
    phantom_ids = [(row_id,) for row_id, uid in rows if uid not in opened]
    with conn:
        conn.executemany("DELETE FROM raw_events WHERE id = ?", phantom_ids)
    return len(phantom_ids)


def _opened_event_uids(spool_path: Path) -> set[str]:
    """event_uids the spool shows a real UserPromptSubmit/SubagentStart for."""
    uids: set[str] = set()
    if not spool_path.exists():
        return uids
    with spool_path.open(errors="replace") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = event.get("hook_event_name")
            if name == "UserPromptSubmit":
                uids.add(_turn_uid(event))
            elif name == "SubagentStart":
                uids.add(_subagent_uid(event))
    return uids


def _apply(conn: sqlite3.Connection, line: str) -> None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return  # malformed line from a crashed/partial write — an expected boundary condition
    handler = _HANDLERS.get(payload.get("hook_event_name"))
    if handler is not None:
        handler(conn, payload)


def _turn_uid(payload: dict[str, Any]) -> str:
    # Some real UserPromptSubmit payloads carry no prompt_id; key those on the
    # open time. Their Stop has none either and takes _close_turn's fallback.
    return (
        f"agent-turn:{payload['session_id']}:"
        f"{payload.get('prompt_id') or payload['_received_at']}"
    )


def _subagent_uid(payload: dict[str, Any]) -> str:
    return f"agent-subagent:{payload['session_id']}:{payload['agent_id']}"


def _open_turn(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    open_or_close_agent_event(
        conn,
        event_uid=_turn_uid(payload),
        ts=payload["_received_at"],
        kind="claude-code-turn",
        title=None,
        payload={"session_id": payload["session_id"], "cwd": payload.get("cwd")},
        closing=False,
    )


def _close_turn(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    close_payload = {
        "last_assistant_message": (payload.get("last_assistant_message") or "")[
            :INTENT_TRUNCATE_CHARS
        ],
        "stop_reason": payload.get("stop_reason"),
        "intent": extract_intent(payload),
    }
    prompt_id = payload.get("prompt_id")
    if prompt_id is None:
        # ponytail: Stop fires without prompt_id in some real payloads (observed
        # live) despite the module docstring's assumption — close the most
        # recently opened still-open turn for this session instead of crashing.
        # event_uid is left untouched, so read-time session_id recovery still works.
        conn.execute(
            """
            UPDATE raw_events
            SET ts_end = :ts, payload = json_patch(COALESCE(payload, '{}'), :payload)
            WHERE id = (
                SELECT id FROM raw_events
                WHERE source = 'agent' AND kind = 'claude-code-turn' AND ts_end IS NULL
                  AND json_extract(payload, '$.session_id') = :session_id
                ORDER BY ts_start DESC LIMIT 1
            )
            """,
            {
                "ts": payload["_received_at"],
                "payload": json.dumps(close_payload),
                "session_id": payload["session_id"],
            },
        )
        return
    open_or_close_agent_event(
        conn,
        event_uid=_turn_uid(payload),
        ts=payload["_received_at"],
        kind="claude-code-turn",
        title=None,
        payload=close_payload,
        closing=True,
    )


def _open_subagent(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    open_or_close_agent_event(
        conn,
        event_uid=_subagent_uid(payload),
        ts=payload["_received_at"],
        kind="claude-code-subagent",
        title=payload.get("agent_type"),
        payload={
            "session_id": payload["session_id"],
            "cwd": payload.get("cwd"),
            "agent_type": payload.get("agent_type"),
        },
        closing=False,
    )


def _close_subagent(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    open_or_close_agent_event(
        conn,
        event_uid=_subagent_uid(payload),
        ts=payload["_received_at"],
        kind="claude-code-subagent",
        title=payload.get("agent_type"),
        payload={
            "last_assistant_message": (payload.get("last_assistant_message") or "")[
                :INTENT_TRUNCATE_CHARS
            ],
            "intent": extract_intent(payload),
        },
        closing=True,
    )


def _sweep_session(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE raw_events SET ts_end = MIN(:now, ts_start + :timeout)
        WHERE source = 'agent' AND ts_end IS NULL
          AND json_extract(payload, '$.session_id') = :session_id
        """,
        {
            "now": payload["_received_at"],
            "timeout": REAP_TIMEOUT_SECONDS,
            "session_id": payload["session_id"],
        },
    )


_HANDLERS = {
    "UserPromptSubmit": _open_turn,
    "Stop": _close_turn,
    "StopFailure": _close_turn,
    "SubagentStart": _open_subagent,
    "SubagentStop": _close_subagent,
    "SessionEnd": _sweep_session,
}
