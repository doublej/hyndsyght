"""Read-only MCP server: bounded, structured, parameterized tools only.

Not a raw `--sql` passthrough — column aliasing, `json_extract`, or string
concatenation in arbitrary SQL can dodge a redaction pass applied *after*
the query runs, and an unbounded query is a local DoS against a large DB.
Every tool below selects only safe columns and redacts titles *inside* the
function, before a row ever leaves Python.
"""

import time
from typing import Any

from fastmcp import FastMCP

from hyndsyght.insights.activity import active_window_rows
from hyndsyght.insights.attention import (
    longest_stretch,
    median_session_length,
    switches_per_hour,
)
from hyndsyght.insights.intervals import day_bounds
from hyndsyght.insights.ledger import three_column
from hyndsyght.mcpserver.redact import redact_title
from hyndsyght.store.query import interval_rows, run_sql

LIST_EVENTS_MAX_LIMIT = 500

mcp: FastMCP = FastMCP("hyndsyght")


@mcp.tool()
def list_recent_events(
    source: str | None = None,
    since_minutes: int = 60,
    limit: int = 100,
    redact: bool = True,
) -> list[dict[str, Any]]:
    """List recently tracked events, most recent first. Titles are redacted by default."""
    since = time.time() - since_minutes * 60
    sql = "SELECT source, kind, title, ts_start, ts_end FROM raw_events WHERE ts_start >= ?"
    params: list[Any] = [since]
    if source is not None:
        sql += " AND source = ?"
        params.append(source)
    sql += " ORDER BY ts_start DESC LIMIT ?"
    params.append(min(max(limit, 1), LIST_EVENTS_MAX_LIMIT))
    rows = run_sql(sql, params=tuple(params))
    for row in rows:
        row["title"] = redact_title(row["title"], enabled=redact)
    return rows


@mcp.tool()
def get_attention_summary(day: str) -> dict[str, float]:
    """Attention Physics summary (longest stretch, switches/hour, median session) for one day."""
    start, end = day_bounds(day)
    intervals = _window_intervals(start, end)
    return {
        "longest_stretch_seconds": longest_stretch(intervals),
        "switches_per_hour": switches_per_hour(intervals, end - start),
        "median_session_seconds": median_session_length(intervals),
    }


@mcp.tool()
def get_ledger_summary(day: str) -> dict[str, float]:
    """Leverage Ledger summary (human/agent/overlap minutes) for one day."""
    start, end = day_bounds(day)
    human_minutes, agent_minutes, overlap_minutes = three_column(
        _window_intervals(start, end),
        interval_rows("agent", start, end),
    )
    return {
        "human_minutes": human_minutes,
        "agent_minutes": agent_minutes,
        "overlap_minutes": overlap_minutes,
    }


def _window_intervals(start: float, end: float) -> list[tuple[float, float]]:
    """AFK-clipped window time, the same rows /api/ledger reads (insights/ledger.py)."""
    return [(row["ts_start"], row["ts_end"]) for row in active_window_rows(start, end)]
