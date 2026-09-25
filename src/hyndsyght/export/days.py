"""The `schema: 1` export: AFK-clipped human seconds per local day and row.

A row is one (project, client, category). Agent time never becomes hours; it
only shows up as `evidence.agent_seconds`, the agent time running alongside the
row. `private.*` time is left out, and time with neither a client nor a
category is only counted in `unclassified_seconds`.
"""

import csv
import io
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from hyndsyght.categorize.match import (
    UNCATEGORIZED,
    categorize,
    client_of,
    payload_match_field,
)
from hyndsyght.categorize.rules import Rules
from hyndsyght.export.project import agent_turns, project_of
from hyndsyght.insights.activity import Spans, clip, day_rows, load_spans
from hyndsyght.insights.intervals import (
    Interval,
    day_bounds,
    intersect_total,
    merge_intervals,
)

SCHEMA = 1
Key = tuple[str | None, str | None, str | None]  # project, client, category


def export_days(since: date, until: date, rules: Rules) -> dict[str, Any]:
    days = [since + timedelta(n) for n in range((until - since).days + 1)]
    start, end = day_bounds(str(since))[0], day_bounds(str(until))[1]
    spans, turns = load_spans(start, end), agent_turns(start, end)
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tz": local_tz_name(),
        "days": [export_day(str(day), spans, turns, rules) for day in days],
    }


def local_tz_name() -> str:
    """The IANA zone the days are cut in: day bounds use the Mac's local time."""
    # ponytail: macOS/Linux symlink layout; read TZ first if this ever runs elsewhere.
    return os.path.realpath("/etc/localtime").split("zoneinfo/")[-1]


def classified_rows(
    spans: Spans, turns: list[dict[str, Any]], rules: Rules, day: str
) -> list[dict[str, Any]]:
    """One day's AFK-clipped window rows, each with its project, client and category."""
    start, end = day_bounds(day)
    day_turns = [t for t in turns if t["ts_start"] < end and t["ts_end"] > start]
    return [classify(row, day_turns, rules) for row in day_rows(spans, start, end)]


def classify(
    row: dict[str, Any], turns: list[dict[str, Any]], rules: Rules
) -> dict[str, Any]:
    payload = json.loads(row["payload"]) if row["payload"] else {}
    app = payload.get("app") or row["title"]
    project = project_of(app, row["ts_start"], row["ts_end"], turns)
    extra = payload_match_field(payload)
    category = categorize(row["title"], row["kind"], rules, extra)
    return {
        "app": app,
        "title": row["title"],
        "project": project,
        "client": client_of(row["title"], rules, extra, project),
        "category": None if category == UNCATEGORIZED else category,
        "interval": (row["ts_start"], row["ts_end"]),
    }


def export_day(
    day: str, spans: Spans, turns: list[dict[str, Any]], rules: Rules
) -> dict[str, Any]:
    items = classified_rows(spans, turns, rules, day)
    groups: dict[Key, list[dict[str, Any]]] = {}
    for item in items:
        if not _is_private(item["category"]):
            groups.setdefault(
                (item["project"], item["client"], item["category"]), []
            ).append(item)
    agents = clip(day_bounds(day), spans.agents)
    unclassified = [i for k, v in groups.items() if k[1:] == (None, None) for i in v]
    rows = [_row(day, k, v, agents) for k, v in groups.items() if k[1:] != (None, None)]
    return {
        "date": day,
        "human_seconds": _seconds(items),
        "unclassified_seconds": _seconds(unclassified),
        "rows": sorted(rows, key=lambda row: row["seconds"], reverse=True),
    }


def _is_private(category: str | None) -> bool:
    return category is not None and category.split(".")[0] == "private"


def _row(
    day: str, key: Key, items: list[dict[str, Any]], agents: list[Interval]
) -> dict[str, Any]:
    project, client, category = key
    human = merge_intervals([item["interval"] for item in items])
    return {
        "id": f"hyndsyght:{day}:{project or '-'}:{client or '-'}:{category or '-'}",
        "project": project,
        "client": client,
        "category": category,
        "seconds": _seconds(items),
        "evidence": {
            "apps": _top(items, "app"),
            "titles": _top(items, "title"),
            "agent_seconds": round(intersect_total(human, agents)),
        },
    }


def _seconds(items: list[dict[str, Any]]) -> int:
    merged = merge_intervals([item["interval"] for item in items])
    return round(sum(end - start for start, end in merged))


def _top(items: list[dict[str, Any]], field: str) -> list[list[Any]]:
    """The three values of `field` with the most time; redacted rows have no title."""
    totals: Counter[str] = Counter()
    for item in items:
        if item[field]:
            totals[item[field]] += item["interval"][1] - item["interval"][0]
    return [[value, round(seconds)] for value, seconds in totals.most_common(3)]


def to_csv(export: dict[str, Any]) -> str:
    """Hours per day and client, rounded to 15 minutes, for a timesheet."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["date", "client", "hours"])
    for day in export["days"]:
        totals: Counter[str] = Counter()
        for row in day["rows"]:
            if row["client"]:
                totals[row["client"]] += row["seconds"]
        for client, seconds in sorted(totals.items()):
            if hours := round(seconds / 900) / 4:
                writer.writerow([day["date"], client, hours])
    return out.getvalue()
