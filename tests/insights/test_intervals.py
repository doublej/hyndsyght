from hyndsyght.insights.intervals import day_bounds, intersect_total, merge_intervals


def test_empty_input_returns_empty() -> None:
    assert merge_intervals([]) == []


def test_disjoint_intervals_are_left_separate() -> None:
    assert merge_intervals([(0, 1), (5, 6)]) == [(0, 1), (5, 6)]


def test_overlapping_intervals_merge() -> None:
    assert merge_intervals([(0, 5), (3, 8)]) == [(0, 8)]


def test_adjacent_intervals_merge() -> None:
    assert merge_intervals([(0, 5), (5, 8)]) == [(0, 8)]


def test_unordered_input_is_sorted_before_merging() -> None:
    assert merge_intervals([(5, 8), (0, 5)]) == [(0, 8)]


def test_contained_interval_is_absorbed() -> None:
    assert merge_intervals([(0, 10), (2, 4)]) == [(0, 10)]


def test_intersect_total_of_disjoint_lists_is_zero() -> None:
    assert intersect_total([(0, 5)], [(10, 15)]) == 0.0


def test_intersect_total_sums_partial_overlaps() -> None:
    # a: 0-5, 10-15 | b: 3-12 -> overlaps 3-5 (2) and 10-12 (2) = 4
    assert intersect_total([(0, 5), (10, 15)], [(3, 12)]) == 4.0


def test_intersect_total_of_identical_intervals_is_the_full_span() -> None:
    assert intersect_total([(0, 5)], [(0, 5)]) == 5.0


def test_day_bounds_spans_exactly_24_hours() -> None:
    start, end = day_bounds("2024-01-15")
    assert end - start == 86400.0
