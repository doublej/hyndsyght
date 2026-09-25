from pathlib import Path

from hyndsyght.categorize.exclude import is_away, should_redact
from hyndsyght.categorize.rules import load_rules


def _rules(tmp_path: Path):
    path = tmp_path / "rules.toml"
    path.write_text(
        '[redact]\npatterns = ["1Password", "Bank"]\n\n[away]\npatterns = ["^loginwindow$"]\n'
    )
    return load_rules(path)


def test_should_redact_matches_pattern(tmp_path: Path) -> None:
    rules = _rules(tmp_path)
    assert should_redact("1Password — Vault", rules) is True
    assert should_redact("Terminal", rules) is False


def test_should_redact_fails_closed_on_missing_title(tmp_path: Path) -> None:
    rules = _rules(tmp_path)
    assert should_redact(None, rules) is False


def test_is_away_matches_pattern(tmp_path: Path) -> None:
    rules = _rules(tmp_path)
    assert is_away("loginwindow", rules) is True
    assert is_away("Terminal", rules) is False


def test_is_away_fails_closed_on_missing_title(tmp_path: Path) -> None:
    rules = _rules(tmp_path)
    assert is_away(None, rules) is False
