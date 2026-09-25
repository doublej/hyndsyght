"""DDL for the single `raw_events` table shared by every event source."""

import sqlite3

CREATE_RAW_EVENTS = """
CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY,
    event_uid TEXT UNIQUE,
    ts_start REAL NOT NULL,
    ts_end REAL,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT,
    payload TEXT,
    created_at REAL NOT NULL
)
"""

CREATE_SOURCE_TS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_raw_events_source_ts ON raw_events(source, ts_start)
"""


# Overlap queries (`ts_end > start AND ts_start < end`) would otherwise scan
# every row since the first one: the per-day cost would grow with all history.
CREATE_SOURCE_TS_END_INDEX = """
CREATE INDEX IF NOT EXISTS idx_raw_events_source_ts_end ON raw_events(source, ts_end)
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_RAW_EVENTS)
    conn.execute(CREATE_SOURCE_TS_INDEX)
    conn.execute(CREATE_SOURCE_TS_END_INDEX)
