import json
from pathlib import Path

from click.testing import CliRunner

from hyndsyght.cli import main


def test_init_creates_db(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "hyndsyght.db").exists()
    assert "hyndsyght setup" in result.output


def test_setup_yes_runs_all_steps_against_tmp_state(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("hyndsyght.setup.wizard.CLAUDE_SETTINGS_PATH", settings_path)
    monkeypatch.setattr("hyndsyght.status.CLAUDE_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(
        "hyndsyght.setup.wizard.UV_TOOL_BIN", tmp_path / "local-bin" / "hyndsyght"
    )
    (tmp_path / "local-bin").mkdir()
    (tmp_path / "local-bin" / "hyndsyght").touch()
    monkeypatch.setattr(
        "hyndsyght.setup.wizard.window_watcher",
        lambda: type("FakeWatcher", (), {"poll": lambda self: None})(),
    )
    monkeypatch.setattr("hyndsyght.setup.daemon.service_install", lambda *_: True)
    monkeypatch.setattr(
        "hyndsyght.setup.daemon.register_in_atlas",
        lambda *_: "project-atlas not found — skipped",
    )

    result = CliRunner().invoke(main, ["setup", "--yes"])

    assert result.exit_code == 0
    assert (tmp_path / "hyndsyght.db").exists()
    assert json.loads(settings_path.read_text())["hooks"]


def test_status_default_output_is_human_readable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "hyndsyght.status.CLAUDE_SETTINGS_PATH", tmp_path / "settings.json"
    )
    CliRunner().invoke(main, ["init"])

    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0
    assert not result.output.strip().startswith("{")
    assert "Run `hyndsyght serve`" in result.output


def test_status_json_flag_round_trips(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "hyndsyght.status.CLAUDE_SETTINGS_PATH", tmp_path / "settings.json"
    )
    CliRunner().invoke(main, ["init"])

    result = CliRunner().invoke(main, ["status", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "daemon_running" in data


def test_serve_no_open_skips_browser(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    opened = []
    monkeypatch.setattr("hyndsyght.cli.webbrowser.open", opened.append)
    monkeypatch.setattr("hyndsyght.cli.uvicorn.run", lambda *a, **k: None)

    CliRunner().invoke(main, ["serve", "--no-open"])

    assert opened == []


def test_serve_without_flag_schedules_browser_open(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    scheduled = []

    class FakeTimer:
        def __init__(self, interval, func, args=()) -> None:
            scheduled.append((interval, args))

        def start(self) -> None:
            pass

    monkeypatch.setattr("hyndsyght.cli.threading.Timer", FakeTimer)
    monkeypatch.setattr("hyndsyght.cli.uvicorn.run", lambda *a, **k: None)

    CliRunner().invoke(main, ["serve"])

    assert scheduled == [(0.6, ("http://127.0.0.1:8420",))]


def test_query_command_outputs_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    CliRunner().invoke(main, ["init"])
    result = CliRunner().invoke(main, ["query", "--sql", "SELECT 1 AS one", "--json"])
    assert result.exit_code == 0
    assert result.output.strip() == '[{"one": 1}]'


def test_mcp_serve_is_registered() -> None:
    result = CliRunner().invoke(main, ["mcp", "serve", "--help"])
    assert result.exit_code == 0


def test_repair_reports_cwd_durations_and_phantoms(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    CliRunner().invoke(main, ["init"])

    result = CliRunner().invoke(main, ["--lang", "en", "repair"])

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        "Restored the project path on 0 agent events.",
        "Capped 0 agent event durations left unbounded.",
        "Removed 0 agent events with no matching start.",
    ]
