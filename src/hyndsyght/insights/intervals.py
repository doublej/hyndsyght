"""Interval-union math shared by Attention Physics and the Leverage Ledger.

Real interval unions instead of per-second buckets: cheaper and precise
regardless of the underlying poll cadence.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

Interval = tuple[float, float]


def day_bounds(day: str) -> tuple[float, float]:
    # Naive local midnights, so each end carries its own date's DST offset.
    start_dt = datetime.combine(date.fromisoformat(day), time())
    return start_dt.timestamp(), (start_dt + timedelta(days=1)).timestamp()


def merge_intervals(intervals: Sequence[Interval]) -> list[Interval]:
    """Sort by start, merge overlapping/adjacent spans into continuous stretches."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def intersect_total(a: Sequence[Interval], b: Sequence[Interval]) -> float:
    """Total overlap between two sorted, non-overlapping interval lists (a two-pointer sweep)."""
    i = j = 0
    total = 0.0
    while i < len(a) and j < len(b):
        start, end = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if start < end:
            total += end - start
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total
