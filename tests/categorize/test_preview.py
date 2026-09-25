from pathlib import Path

from click.testing import CliRunner

from hyndsyght.cli import main


def test_categorize_preview_classifies_title(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    CliRunner().invoke(main, ["init"])
    result = CliRunner().invoke(main, ["categorize", "preview", "Terminal — zsh"])
    assert result.exit_code == 0
    assert result.output.strip() == "dev"


def test_categorize_preview_without_title_lists_rules(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    CliRunner().invoke(main, ["init"])
    result = CliRunner().invoke(main, ["categorize", "preview"])
    assert result.exit_code == 0
    assert "redact:" in result.output
    assert "away:" in result.output
