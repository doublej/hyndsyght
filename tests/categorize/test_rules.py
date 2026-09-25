from pathlib import Path

import pytest

from hyndsyght.categorize.rules import (
    InvalidPatternError,
    UnknownCategoryError,
    add_pattern,
    ensure_default,
    load_rules,
    remove_pattern,
)


def test_ensure_default_writes_template_once(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)
    written = path.read_text()
    ensure_default(path)
    assert path.read_text() == written


def test_load_rules_parses_categories_and_hashes_content(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text(
        '[redact]\npatterns = ["Secret"]\n\n[away]\npatterns = ["Locked"]\n\n'
        '[categories]\n"dev" = ["Code"]\n'
    )
    rules = load_rules(path)
    assert [p.pattern for p in rules.redact_patterns] == ["Secret"]
    assert [p.pattern for p in rules.away_patterns] == ["Locked"]
    assert rules.categories == (("dev", (rules.categories[0][1][0],)),)

    path.write_text(
        '[redact]\npatterns = ["Other"]\n\n[away]\npatterns = []\n\n'
        '[categories]\n"dev" = ["Code"]\n'
    )
    assert load_rules(path).file_hash != rules.file_hash


def test_add_pattern_preserves_existing_content(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    rules = add_pattern("dev", "Ghostty", path)

    dev = dict(rules.categories)["dev"]
    assert [p.pattern for p in dev][-1] == "Ghostty"
    assert "Terminal" in [p.pattern for p in dev]
    assert "communication" in dict(rules.categories)
    assert "1Password" in [p.pattern for p in rules.redact_patterns]


def test_add_pattern_creates_new_category(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    rules = add_pattern("gaming", "Steam", path)

    assert dict(rules.categories)["gaming"][0].pattern == "Steam"


def test_add_pattern_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    add_pattern("dev", "Ghostty", path)
    rules = add_pattern("dev", "Ghostty", path)

    patterns = [p.pattern for p in dict(rules.categories)["dev"]]
    assert patterns.count("Ghostty") == 1


def test_add_pattern_rejects_bad_regex(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    with pytest.raises(InvalidPatternError):
        add_pattern("dev", "[unclosed", path)


def test_add_pattern_writes_atomically(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    add_pattern("dev", "Ghostty", path)

    assert not path.with_suffix(".toml.tmp").exists()


def test_remove_pattern_removes_empty_category(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    rules = remove_pattern("media", "Spotify", path)
    rules = remove_pattern("media", "Music", path)
    rules = remove_pattern("media", "YouTube", path)

    assert "media" not in dict(rules.categories)


def test_remove_pattern_unknown_category_raises(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    ensure_default(path)

    with pytest.raises(UnknownCategoryError):
        remove_pattern("nonexistent", "X", path)


def test_clients_survive_a_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text(
        '[categories]\n"dev" = ["Code"]\n\n[clients]\n"acme.globex" = ["Globex", "web/globex"]\n'
    )

    rules = add_pattern("dev", "Ghostty", path)

    assert [(name, [p.pattern for p in ps]) for name, ps in rules.clients] == [
        ("acme.globex", ["Globex", "web/globex"])
    ]
