from pathlib import Path

from hyndsyght.export.project import agent_turns, project_of, repo_path
from hyndsyght.store.db import connect, init_db
from hyndsyght.store.events import write_interval

HOME = str(Path.home())


def test_repo_path_reduces_a_cwd_to_group_and_repo() -> None:
    assert repo_path(f"{HOME}/dev/python/finances/src/x") == "python/finances"
    assert repo_path(f"{HOME}/Documents/development/web/offerte") == "web/offerte"
    assert repo_path(f"{HOME}/dev/python") is None
    assert repo_path("/tmp/python/finances") is None
    assert repo_path(None) is None


def turn(cwd: str, start: float, end: float) -> dict[str, object]:
    return {"cwd": f"{HOME}/dev/{cwd}", "ts_start": start, "ts_end": end}


def test_project_of_prefers_the_prompt_submitted_during_the_row() -> None:
    turns = [turn("python/long", 0, 1000), turn("python/typed", 500, 520)]
    assert project_of("iTerm2", 400, 600, turns) == "python/typed"


def test_project_of_falls_back_to_the_longest_overlap() -> None:
    turns = [turn("python/short", 0, 110), turn("python/long", 50, 1000)]
    assert project_of("Code", 100, 300, turns) == "python/long"


def test_project_of_ignores_other_apps_and_idle_terminals() -> None:
    turns = [turn("python/finances", 0, 1000)]
    assert project_of("Google Chrome", 100, 200, turns) is None
    assert project_of("iTerm2", 2000, 2100, turns) is None


def test_agent_turns_reads_closed_rows_with_a_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db()
    with connect(tmp_path / "hyndsyght.db") as conn:
        for payload in ({"cwd": "/x"}, {"session_id": "s"}):
            write_interval(
                conn,
                source="agent",
                kind="claude-code-turn",
                title=None,
                ts_start=10.0,
                ts_end=20.0,
                payload=payload,
            )
    assert agent_turns(0, 100) == [{"ts_start": 10.0, "ts_end": 20.0, "cwd": "/x"}]
