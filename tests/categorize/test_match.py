from pathlib import Path

from hyndsyght.categorize.match import UNCATEGORIZED, categorize, client_of
from hyndsyght.categorize.rules import load_rules


def _rules(tmp_path: Path, contents: str):
    path = tmp_path / "rules.toml"
    path.write_text(contents)
    return load_rules(path)


def test_categorize_picks_deepest_matching_category(tmp_path: Path) -> None:
    rules = _rules(
        tmp_path,
        '[categories]\n"dev" = ["Chrome"]\n"dev.browser" = ["Chrome"]\n',
    )
    assert categorize("Chrome — new tab", "window", rules) == "dev.browser"


def test_categorize_returns_uncategorized_when_nothing_matches(tmp_path: Path) -> None:
    rules = _rules(tmp_path, '[categories]\n"dev" = ["Chrome"]\n')
    assert categorize("Finder", "window", rules) == UNCATEGORIZED


def test_categorize_cache_invalidates_when_rules_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text('[categories]\n"dev" = ["Terminal"]\n')
    rules_v1 = load_rules(path)
    assert categorize("Terminal", "window", rules_v1) == "dev"

    path.write_text('[categories]\n"other" = ["Terminal"]\n')
    rules_v2 = load_rules(path)
    assert categorize("Terminal", "window", rules_v2) == "other"


def test_categorize_matches_extra_field_when_title_does_not(tmp_path: Path) -> None:
    rules = _rules(tmp_path, '[categories]\n"media" = ["Spotify"]\n')
    assert categorize("Benzo", "playing", rules, "Spotify") == "media"
    assert categorize("Benzo", "playing", rules) == UNCATEGORIZED


def test_categorize_window_title_only_behaviour_is_unchanged(tmp_path: Path) -> None:
    rules = _rules(tmp_path, '[categories]\n"dev" = ["iTerm2"]\n')
    assert categorize("iTerm2", "window", rules, "iTerm2") == "dev"
    assert categorize("iTerm2", "window", rules) == "dev"
    assert categorize("Finder", "window", rules, "Finder") == UNCATEGORIZED


def test_categorize_cache_does_not_bleed_across_extra_field(tmp_path: Path) -> None:
    rules = _rules(
        tmp_path, '[categories]\n"media" = ["Spotify"]\n"dev" = ["iTerm2"]\n'
    )
    assert categorize("Some Track", "playing", rules, "Spotify") == "media"
    assert categorize("Some Track", "playing", rules, "iTerm2") == "dev"
    assert categorize("Some Track", "playing", rules) == UNCATEGORIZED


def test_pattern_that_can_match_empty_does_not_swallow_absent_fields(
    tmp_path: Path,
) -> None:
    rules = _rules(tmp_path, '[categories]\n"greedy" = ["x*"]\n')
    # An agent event carries no title and, before its project is restored, no
    # payload field either. A zero-width-matchable pattern must not claim it
    # by matching the empty string.
    assert categorize(None, "claude-code-turn", rules, None) == UNCATEGORIZED


def test_client_of_matches_on_its_own_axis(tmp_path: Path) -> None:
    rules = _rules(
        tmp_path,
        '[categories]\n"dev" = ["iTerm"]\n\n'
        '[clients]\n"acme" = ["Globex"]\n"acme.globex" = ["Globex", "web/globex"]\n',
    )
    assert categorize("Globex board", "window", rules, "iTerm2") == "dev"
    assert client_of("Globex board", rules, "iTerm2") == "acme.globex"
    assert client_of("✳ umber-weasel", rules, "iTerm2", "web/globex") == "acme.globex"
    assert client_of("✳ umber-weasel", rules, "iTerm2") is None


def test_client_of_breaks_equal_depth_ties_by_file_order(tmp_path: Path) -> None:
    rules = _rules(tmp_path, '[clients]\n"a.one" = ["x"]\n"b.two" = ["x"]\n')
    assert client_of("x", rules) == "a.one"
