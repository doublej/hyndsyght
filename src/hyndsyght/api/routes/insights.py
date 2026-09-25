"""GET /api/attention, /api/ledger, /api/trend, /api/categories."""

import json
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter

from hyndsyght.categorize.match import categorize, payload_match_field
from hyndsyght.categorize.rules import load_rules
from hyndsyght.insights.activity import active_window_rows
from hyndsyght.insights.attention import (
    longest_stretch,
    median_session_length,
    switches_per_hour,
)
from hyndsyght.insights.categories import category_breakdown
from hyndsyght.insights.intervals import Interval, day_bounds
from hyndsyght.insights.ledger import three_column
from hyndsyght.store.query import interval_rows, run_sql

DEFAULT_WINDOW_SECONDS = 86400


def register_insights_routes(router: APIRouter) -> None:
    @router.get("/api/attention")
    def attention_summary(
        since: float | None = None,
        until: float | None = None,
        source: str = "window",
        category: str | None = None,
    ) -> dict[str, float]:
        window_end = until if until is not None else time.time()
        window_start = (
            since if since is not None else window_end - DEFAULT_WINDOW_SECONDS
        )
        intervals = _filtered_intervals(source, window_start, window_end, category)
        return {
            "longest_stretch_seconds": longest_stretch(intervals),
            "switches_per_hour": switches_per_hour(
                intervals, window_end - window_start
            ),
            "median_session_seconds": median_session_length(intervals),
        }

    @router.get("/api/ledger")
    def ledger_summary(day: str | None = None) -> dict[str, float]:
        target_day = day or datetime.now().astimezone().date().isoformat()
        start, end = day_bounds(target_day)
        return _ledger_for_window(start, end)

    @router.get("/api/trend")
    def trend(
        metric: str = "ledger", days: int = 14, source: str = "window"
    ) -> list[dict[str, Any]]:
        today = datetime.now().astimezone().date()
        results = []
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            start, end = day_bounds(day.isoformat())
            if metric == "attention":
                intervals = _intervals(source, start, end)
                value: dict[str, float] = {
                    "longest_stretch_seconds": longest_stretch(intervals),
                    "switches_per_hour": switches_per_hour(intervals, end - start),
                    "median_session_seconds": median_session_length(intervals),
                }
            else:
                value = _ledger_for_window(start, end)
            results.append({"day": day.isoformat(), **value})
        return results

    @router.get("/api/categories")
    def categories_breakdown(
        since: float | None = None, until: float | None = None, source: str = "window"
    ) -> list[dict[str, Any]]:
        window_end = until if until is not None else time.time()
        window_start = (
            since if since is not None else window_end - DEFAULT_WINDOW_SECONDS
        )
        rows = _titled_rows(source, window_start, window_end)
        return category_breakdown(rows, load_rules())


def _ledger_for_window(start: float, end: float) -> dict[str, float]:
    human_minutes, agent_minutes, overlap_minutes = three_column(
        _intervals("window", start, end), interval_rows("agent", start, end)
    )
    return {
        "human_minutes": human_minutes,
        "agent_minutes": agent_minutes,
        "overlap_minutes": overlap_minutes,
    }


def _intervals(source: str, start: float, end: float) -> list[Interval]:
    if source != "window":
        return interval_rows(source, start, end)
    return [(row["ts_start"], row["ts_end"]) for row in active_window_rows(start, end)]


def _titled_rows(source: str, start: float, end: float) -> list[dict[str, Any]]:
    if source == "window":
        return active_window_rows(start, end)
    return run_sql(
        "SELECT title, kind, payload, ts_start, ts_end FROM raw_events"
        " WHERE source = ? AND ts_start >= ? AND ts_start < ? AND ts_end IS NOT NULL",
        params=(source, start, end),
    )


def _filtered_intervals(
    source: str, start: float, end: float, category: str | None
) -> list[Interval]:
    if category is None:
        return _intervals(source, start, end)
    rules = load_rules()
    return [
        (row["ts_start"], row["ts_end"])
        for row in _titled_rows(source, start, end)
        if categorize(
            row["title"],
            row["kind"],
            rules,
            payload_match_field(json.loads(row["payload"]) if row["payload"] else {}),
        )
        == category
    ]
