from hyndsyght.insights.attention import (
    longest_stretch,
    median_session_length,
    switches_per_hour,
)


def test_longest_stretch_of_empty_input_is_zero() -> None:
    assert longest_stretch([]) == 0.0


def test_longest_stretch_picks_the_longest_merged_span() -> None:
    intervals = [(0, 5), (5, 8), (100, 101)]
    assert longest_stretch(intervals) == 8.0


def test_median_session_length_of_empty_input_is_zero() -> None:
    assert median_session_length([]) == 0.0


def test_median_session_length_over_merged_sessions() -> None:
    # merges to sessions of length 10 and 2 -> median 6
    intervals = [(0, 5), (5, 10), (20, 22)]
    assert median_session_length(intervals) == 6.0


def test_switches_per_hour_counts_raw_intervals_over_the_window() -> None:
    intervals = [(0, 1), (1, 2), (2, 3), (3, 4)]
    assert switches_per_hour(intervals, window_seconds=3600) == 4.0


def test_switches_per_hour_of_zero_window_is_zero() -> None:
    assert switches_per_hour([(0, 1)], window_seconds=0) == 0.0
