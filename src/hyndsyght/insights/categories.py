"""Category breakdown: time-per-category over a window, via merge_intervals."""

import json
from collections.abc import Sequence
from typing import Any

from hyndsyght.categorize.match import categorize, payload_match_field
from hyndsyght.categorize.rules import Rules
from hyndsyght.insights.intervals import Interval, merge_intervals


def category_breakdown(
    rows: Sequence[dict[str, Any]], rules: Rules
) -> list[dict[str, Any]]:
    by_category: dict[str, list[Interval]] = {}
    for row in rows:
        payload = json.loads(row["payload"]) if row.get("payload") else {}
        category = categorize(
            row["title"], row["kind"], rules, payload_match_field(payload)
        )
        by_category.setdefault(category, []).append((row["ts_start"], row["ts_end"]))
    breakdown = [
        {
            "category": category,
            "seconds": sum(end - start for start, end in merge_intervals(intervals)),
        }
        for category, intervals in by_category.items()
    ]
    return sorted(breakdown, key=lambda entry: entry["seconds"], reverse=True)
