from hyndsyght.insights.ledger import three_column


def test_empty_input_is_all_zero() -> None:
    assert three_column([], []) == (0.0, 0.0, 0.0)


def test_agent_minutes_sum_not_union_for_parallel_subagents() -> None:
    # two subagents running the same 10-minute stretch in parallel
    human, agent, overlap = three_column([(0, 600)], [(0, 600), (0, 600)])
    assert human == 10.0
    assert agent == 20.0  # summed, not unioned
    assert overlap == 10.0  # intersect of *unioned* timelines, not double-counted


def test_overlap_is_bounded_by_the_shorter_unioned_span() -> None:
    # human active 0-600 (10 min), agent active 300-900 (10 min) -> overlap 300-600 (5 min)
    human, agent, overlap = three_column([(0, 600)], [(300, 900)])
    assert human == 10.0
    assert agent == 10.0
    assert overlap == 5.0
