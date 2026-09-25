"""Write paths for raw_events — deliberately two of them.

Baseline-watcher rows are written and updated directly by the daemon that
owns them (no cross-process replay risk). Agent-sourced rows are replayed
from a spool after a crash, so they're upserted by a stable `event_uid`
instead.
"""

import json
import sqlite3
import time
from typing import Any


def write_interval(
    conn: sqlite3.Connection,
    *,
    source: str,
    kind: str,
    title: str | None,
    ts_start: float,
    ts_end: float | None,
    payload: dict[str, Any] | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO raw_events (ts_start, ts_end, source, kind, title, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts_start,
            ts_end,
            source,
            kind,
            title,
            json.dumps(payload) if payload else None,
            time.time(),
        ),
    )
    return int(cursor.lastrowid)  # type: ignore[arg-type]


def update_interval_end(conn: sqlite3.Connection, row_id: int, ts_end: float) -> None:
    conn.execute("UPDATE raw_events SET ts_end = ? WHERE id = ?", (ts_end, row_id))


def open_or_close_agent_event(
    conn: sqlite3.Connection,
    *,
    event_uid: str,
    ts: float,
    kind: str,
    title: str | None,
    payload: dict[str, Any] | None,
    closing: bool,
) -> None:
    params = {
        "event_uid": event_uid,
        "ts": ts,
        "kind": kind,
        "title": title,
        "payload": json.dumps(payload) if payload else None,
        "now": time.time(),
    }
    if closing:
        # A close with no matching open row must not insert one — it has no
        # session or project to attribute the time to. Just update, if open.
        conn.execute(
            "UPDATE raw_events SET ts_end = :ts, payload = json_patch("
            "COALESCE(payload, '{}'), COALESCE(:payload, '{}')) "
            "WHERE event_uid = :event_uid AND ts_end IS NULL",
            params,
        )
        return
    conn.execute(
        """
        INSERT INTO raw_events (event_uid, ts_start, ts_end, source, kind, title, payload, created_at)
        VALUES (:event_uid, :ts, NULL, 'agent', :kind, :title, :payload, :now)
        ON CONFLICT(event_uid) DO NOTHING
        """,
        params,
    )


def session_id_from_uid(event_uid: str | None) -> str | None:
    """The session an agent event belongs to, recovered from its event_uid.

    Minted here as "agent-turn:{session_id}:{prompt_id}" and
    "agent-subagent:{session_id}:{agent_id}", so this is the one place that
    knows the shape.
    """
    if not event_uid:
        return None
    parts = event_uid.split(":")
    return parts[1] if len(parts) > 1 else None
