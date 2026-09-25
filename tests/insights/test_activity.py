from pathlib import Path

from hyndsyght.categorize.rules import load_rules
from hyndsyght.insights.activity import app_runs, clip, hourly_minutes


def test_clip_keeps_only_the_pieces_inside_active_spans() -> None:
    # one window row spanning a night, active 0-100 and 500-600
    assert clip((50, 550), [(0, 100), (500, 600)]) == [(50, 100), (500, 550)]


def test_clip_drops_an_interval_entirely_inside_a_gap() -> None:
    assert clip((200, 300), [(0, 100), (500, 600)]) == []


def test_hourly_minutes_splits_across_hour_boundaries() -> None:
    hours = hourly_minutes([(3000, 4200)], day_start=0)
    assert hours[0] == 10.0 and hours[1] == 10.0 and sum(hours) == 20.0


def row(title: str, app: str, start: float, end: float) -> dict[str, object]:
    payload = f'{{"app": "{app}"}}'
    return {
        "title": title,
        "kind": "window",
        "payload": payload,
        "ts_start": start,
        "ts_end": end,
    }


def test_app_runs_join_consecutive_rows_on_the_same_app(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text('[categories]\n"dev" = ["iTerm"]\n')
    rules = load_rules(path)
    runs = app_runs(
        [
            row("tab one", "iTerm2", 0, 10),
            row("tab two", "iTerm2", 10, 30),
            row("inbox", "Mail", 30, 40),
            row("tab one", "iTerm2", 40, 50),
        ],
        rules,
    )
    assert [(r["app"], r["start"], r["end"]) for r in runs] == [
        ("iTerm2", 0, 30),
        ("Mail", 30, 40),
        ("iTerm2", 40, 50),
    ]
    assert runs[0]["category"] == "dev"
