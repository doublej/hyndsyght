"""Read-only `--sql` passthrough for ad-hoc queries."""

import sqlite3
from pathlib import Path
from typing import Any

from hyndsyght import paths


def run_sql(
    sql: str, db_path: Path | None = None, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    path = db_path or paths.db_path()
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def interval_rows(source: str, start: float, end: float) -> list[tuple[float, float]]:
    rows = run_sql(
        "SELECT ts_start, ts_end FROM raw_events"
        " WHERE source = ? AND ts_start >= ? AND ts_start < ? AND ts_end IS NOT NULL",
        params=(source, start, end),
    )
    return [(row["ts_start"], row["ts_end"]) for row in rows]
