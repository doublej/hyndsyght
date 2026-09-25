"""Activity: window time clipped to AFK-active spans, summarised per local day.

The window watcher recorded straight through absences until the daemon learned
to close its row on AFK, so history holds window rows spanning whole nights.
Clipping at read time against the `afk`/`active` spans repairs that history
without touching stored rows.
"""

import bisect
import json
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from hyndsyght.categorize.match import categorize, payload_match_field
from hyndsyght.categorize.rules import Rules
from hyndsyght.insights.intervals import (
    Interval,
    day_bounds,
    intersect_total,
    merge_intervals,
)
from hyndsyght.store.query import run_sql

HOUR = 3600
# ponytail: rows longer than this are stale-capture history (Aug 2026, stuck
# for days) and stay on their start day; a real session rarely crosses midnight
# in one row this long. Raise it if late sessions go missing.
CARRY_OVER_MAX = 4 * HOUR


def clip(interval: Interval, spans: Sequence[Interval]) -> list[Interval]:
    """The pieces of `interval` inside sorted, merged `spans`."""
    start, end = interval
    i = bisect.bisect_right(spans, start, key=lambda span: span[1])
    pieces = []
    while i < len(spans) and spans[i][0] < end:
        piece = (max(start, spans[i][0]), min(end, spans[i][1]))
        if piece[0] < piece[1]:
            pieces.append(piece)
        i += 1
    return pieces


@dataclass(frozen=True)
class Spans:
    """What `day_summary` reads, loaded once so a range of days costs one scan."""

    windows: list[dict[str, Any]]  # unclipped, sorted by ts_start
    active: list[Interval]  # merged afk/active spans
    agents: list[Interval]  # merged agent spans


def load_spans(start: float, end: float) -> Spans:
    return Spans(
        _window_rows(start, end),
        merge_intervals(_spans(start, end, "afk", "active")),
        merge_intervals(_spans(start, end, "agent")),
    )


def active_window_rows(start: float, end: float) -> list[dict[str, Any]]:
    active = merge_intervals(_spans(start, end, "afk", "active"))
    return _clip_to_active(_window_rows(start, end), start, end, active)


def day_rows(spans: Spans, start: float, end: float) -> list[dict[str, Any]]:
    earliest = start - CARRY_OVER_MAX
    lo = bisect.bisect_left(spans.windows, earliest, key=lambda row: row["ts_start"])
    hi = bisect.bisect_left(spans.windows, end, key=lambda row: row["ts_start"])
    active = clip((start, end), spans.active)
    return _clip_to_active(spans.windows[lo:hi], start, end, active)


def _window_rows(start: float, end: float) -> list[dict[str, Any]]:
    return run_sql(
        "SELECT title, kind, payload, ts_start, ts_end FROM raw_events"
        " WHERE source = 'window' AND ts_start >= ? AND ts_start < ?"
        " AND ts_end > ? ORDER BY ts_start",
        params=(start - CARRY_OVER_MAX, end, start),
    )


def _clip_to_active(
    rows: list[dict[str, Any]], start: float, end: float, active: list[Interval]
) -> list[dict[str, Any]]:
    """Rows cut to `active`; a row from before `start` counts only if it is short."""
    if not active:  # no AFK data here: trust the rows that start here, as recorded
        return [row for row in rows if start <= row["ts_start"] < end]
    return [
        {**row, "ts_start": piece[0], "ts_end": piece[1]}
        for row in rows
        if row["ts_start"] >= start or row["ts_end"] - row["ts_start"] <= CARRY_OVER_MAX
        for piece in clip((row["ts_start"], row["ts_end"]), active)
    ]


def _spans(
    start: float, end: float, source: str, kind: str | None = None
) -> list[Interval]:
    rows = run_sql(
        "SELECT ts_start, ts_end FROM raw_events WHERE source = ?"
        " AND (? IS NULL OR kind = ?) AND ts_end > ? AND ts_start < ?",
        params=(source, kind, kind, start, end),
    )
    return [(max(r["ts_start"], start), min(r["ts_end"], end)) for r in rows]


def app_runs(rows: Sequence[dict[str, Any]], rules: Rules) -> list[dict[str, Any]]:
    """Consecutive rows on the same app and category, joined into one run."""
    runs: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        app = payload.get("app") or row["title"] or "?"
        category = categorize(
            row["title"], row["kind"], rules, payload_match_field(payload)
        )
        last = runs[-1] if runs else None
        if (
            last
            and (last["app"], last["category"]) == (app, category)
            and (row["ts_start"] <= last["end"] + 1)
        ):
            last["end"] = max(last["end"], row["ts_end"])
            continue
        runs.append(
            {
                "app": app,
                "category": category,
                "title": row["title"],
                "start": row["ts_start"],
                "end": row["ts_end"],
            }
        )
    return runs


def hourly_minutes(intervals: Sequence[Interval], day_start: float) -> list[float]:
    # ponytail: fixed 3600s buckets, so a DST-change day misfiles one hour.
    hours = [0.0] * 24
    for start, end in intervals:
        while start < end:
            bucket = int((start - day_start) // HOUR)
            bucket_end = min(end, day_start + (bucket + 1) * HOUR)
            if 0 <= bucket < 24:
                hours[bucket] += (bucket_end - start) / 60
            start = bucket_end
    return hours


def day_summary(day: str, rules: Rules, spans: Spans | None = None) -> dict[str, Any]:
    start, end = day_bounds(day)
    spans = spans or load_spans(start, end)
    runs = app_runs(day_rows(spans, start, end), rules)
    human = merge_intervals([(r["start"], r["end"]) for r in runs])
    agents = clip((start, end), spans.agents)
    agent_seconds = _total(agents)
    focus = max(runs, key=lambda r: r["end"] - r["start"], default=None)
    gaps = [(a[1], b[0]) for a, b in pairwise(human)]
    pause = max(gaps, key=lambda g: g[1] - g[0], default=None)
    return {
        "day": day,
        "active_seconds": _total(human),
        "first_ts": human[0][0] if human else None,
        "last_ts": human[-1][1] if human else None,
        "switches": max(len(runs) - 1, 0),
        "break_start": pause[0] if pause else None,
        "break_seconds": pause[1] - pause[0] if pause else 0.0,
        "focus_app": focus["app"] if focus else None,
        "focus_seconds": focus["end"] - focus["start"] if focus else 0.0,
        "agent_seconds": agent_seconds,
        "agent_away_seconds": agent_seconds - intersect_total(human, agents),
        "hours": hourly_minutes(human, start),
        "runs": runs,
        "agents": agents,
    }


def app_totals(runs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    for run in runs:
        totals[run["app"]] = totals.get(run["app"], 0.0) + run["end"] - run["start"]
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [{"app": app, "seconds": seconds} for app, seconds in ordered]


def _total(intervals: Sequence[Interval]) -> float:
    return sum(end - start for start, end in intervals)


def recorded_bundle(app: str) -> str | None:
    """The .app bundle the window watcher last saw behind `app`."""
    rows = run_sql(
        "SELECT json_extract(payload, '$.bundle') AS bundle FROM raw_events"
        " WHERE source = 'window' AND json_extract(payload, '$.app') = ?"
        " AND json_extract(payload, '$.bundle') IS NOT NULL"
        " ORDER BY id DESC LIMIT 1",
        params=(app,),
    )
    return rows[0]["bundle"] if rows else None
