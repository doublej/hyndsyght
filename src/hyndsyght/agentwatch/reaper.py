"""Safety net, not the primary close mechanism — Stop/SubagentStop/SessionEnd
handle the common case. This only catches what even SessionEnd missed
(SIGKILL, power loss): anything still open past a generous timeout.
"""

import sqlite3
import time

REAP_TIMEOUT_SECONDS = 45 * 60


def reap(conn: sqlite3.Connection, now: float | None = None) -> int:
    now = now if now is not None else time.time()
    cutoff = now - REAP_TIMEOUT_SECONDS
    cursor = conn.execute(
        "UPDATE raw_events SET ts_end = MIN(?, ts_start + ?)"
        " WHERE source = 'agent' AND ts_end IS NULL AND ts_start < ?",
        (now, REAP_TIMEOUT_SECONDS, cutoff),
    )
    return cursor.rowcount


def recap_reaped_durations(conn: sqlite3.Connection) -> int:
    """Cap agent rows the old uncapped reaper/session-sweep left running for days.

    A genuine Stop/SubagentStop close always merges a `last_assistant_message`
    key onto the row (store/events.py); reap() and ingest.py's session sweep
    never touch payload, so its absence marks a row one of those closed
    instead. Idempotent: a row already at or under the cap is left alone.
    """
    cursor = conn.execute(
        "UPDATE raw_events SET ts_end = ts_start + ?"
        " WHERE source = 'agent' AND ts_end IS NOT NULL"
        "   AND ts_end - ts_start > ?"
        "   AND json_extract(payload, '$.last_assistant_message') IS NULL",
        (REAP_TIMEOUT_SECONDS, REAP_TIMEOUT_SECONDS),
    )
    return cursor.rowcount
