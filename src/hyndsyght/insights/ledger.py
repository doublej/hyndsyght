"""Leverage Ledger: human vs. agent time and their overlap for one day. No actuation.

agent_minutes sums each raw interval's duration rather than unioning it —
deliberate: three subagents running 20 minutes each in parallel is 60
agent-minutes of real leverage, and unioning would erase exactly the
parallelism this metric exists to show. overlap_minutes intersects the
*unioned* timelines on each side, so two overlapping agents during the same
human-active minute don't inflate overlap past that one real minute.
"""

from collections.abc import Sequence

from hyndsyght.insights.intervals import Interval, intersect_total, merge_intervals


def three_column(
    human_intervals: Sequence[Interval], agent_intervals: Sequence[Interval]
) -> tuple[float, float, float]:
    human_merged = merge_intervals(human_intervals)
    agent_merged = merge_intervals(agent_intervals)
    human_minutes = sum(end - start for start, end in human_merged) / 60
    agent_minutes = sum(end - start for start, end in agent_intervals) / 60
    overlap_minutes = intersect_total(human_merged, agent_merged) / 60
    return human_minutes, agent_minutes, overlap_minutes
