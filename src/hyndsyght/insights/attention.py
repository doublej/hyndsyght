"""Attention Physics: pure descriptive stats over merged intervals. No actuation."""

import statistics
from collections.abc import Sequence

from hyndsyght.insights.intervals import Interval, merge_intervals


def longest_stretch(intervals: Sequence[Interval]) -> float:
    merged = merge_intervals(intervals)
    return max((end - start for start, end in merged), default=0.0)


def median_session_length(intervals: Sequence[Interval]) -> float:
    durations = [end - start for start, end in merge_intervals(intervals)]
    return statistics.median(durations) if durations else 0.0


def switches_per_hour(intervals: Sequence[Interval], window_seconds: float) -> float:
    if window_seconds <= 0:
        return 0.0
    return len(intervals) / (window_seconds / 3600)
