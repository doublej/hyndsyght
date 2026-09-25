from datetime import date
from pathlib import Path

from click.testing import CliRunner

from hyndsyght.categorize.rules import Rules, ensure_default
from hyndsyght.cli import main
from hyndsyght.export.tester import Entry, entries_between, summarize
from hyndsyght.store.db import init_db

DAY = date(2026, 9, 24)  # the fixture day in conftest.py


def test_tester_matches_on_the_app_and_project_like_the_export(rules: Rules) -> None:
    entries = entries_between(DAY, DAY, rules)
    categories = {
        name: dict(labels) for name, _, labels in summarize(entries, "category")
    }
    clients = {name: dict(labels) for name, _, labels in summarize(entries, "client")}
    # the title alone matches nothing: the app and the agent's project do
    assert categories["dev"] == {"✳ umber-weasel [python/finances]": 3600}
    assert clients["initech"] == {"✳ umber-weasel [python/finances]": 3600}
    assert categories["business.ops.admin"] == {"1Password": 1800}  # redacted
    assert categories["uncategorized"] == {
        "Finder": 900,
        f"{Path.home()}/dev/python/finances": 1800,  # the agent turn's cwd
    }


def test_tester_command_reports_an_empty_range(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db()
    ensure_default()
    result = CliRunner().invoke(main, ["--lang", "en", "categorize", "test"])
    assert result.exit_code == 0
    assert result.output.startswith("No activity in the last 7 days.")


def test_tester_command_prints_hours_per_category_and_client(
    rules: Rules, monkeypatch
) -> None:
    entries = [Entry("dev", "acme.globex", "Globex board", 5400.0)]
    monkeypatch.setattr("hyndsyght.export.tester.entries_between", lambda *_: entries)
    result = CliRunner().invoke(main, ["--lang", "en", "categorize", "test"])
    assert result.output == (
        "Categories\n  dev  1.5h\n       1.5h  Globex board\n"
        "Clients\n  acme.globex  1.5h\n       1.5h  Globex board\n"
    )
