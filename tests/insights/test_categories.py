from pathlib import Path

from hyndsyght.categorize.rules import load_rules
from hyndsyght.insights.categories import category_breakdown


def _rules(tmp_path: Path, contents: str):
    path = tmp_path / "rules.toml"
    path.write_text(contents)
    return load_rules(path)


def test_category_breakdown_sums_merged_seconds_per_category(tmp_path: Path) -> None:
    rules = _rules(tmp_path, '[categories]\n"dev" = ["Terminal"]\n')
    rows = [
        {"title": "Terminal", "kind": "app", "ts_start": 0.0, "ts_end": 60.0},
        {"title": "Terminal", "kind": "app", "ts_start": 60.0, "ts_end": 120.0},
        {"title": "Finder", "kind": "app", "ts_start": 200.0, "ts_end": 230.0},
    ]

    breakdown = category_breakdown(rows, rules)

    assert breakdown[0] == {"category": "dev", "seconds": 120.0}
    assert breakdown[1]["category"] == "uncategorized"
    assert breakdown[1]["seconds"] == 30.0
