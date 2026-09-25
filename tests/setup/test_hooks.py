import json
from pathlib import Path
from typing import Any

from hyndsyght.setup import hooks
from hyndsyght.status import HOOK_COMMAND, REQUIRED_HOOKS


def _hook_block(command: str) -> list[dict[str, Any]]:
    return [{"hooks": [{"type": "command", "command": command}]}]


def test_install_creates_settings_file_when_missing(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    added = hooks.install(settings)
    assert all(added.values())
    data = json.loads(settings.read_text())
    for event in REQUIRED_HOOKS:
        commands = [h["command"] for b in data["hooks"][event] for h in b["hooks"]]
        assert HOOK_COMMAND in commands


def test_install_appends_alongside_unrelated_existing_hooks(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": _hook_block("other-tool run"),
                    "SessionEnd": _hook_block("atlas agent-log session-end"),
                }
            }
        )
    )

    hooks.install(settings)

    data = json.loads(settings.read_text())
    stop_commands = [h["command"] for b in data["hooks"]["Stop"] for h in b["hooks"]]
    assert "other-tool run" in stop_commands
    assert HOOK_COMMAND in stop_commands
    session_end_commands = [
        h["command"] for b in data["hooks"]["SessionEnd"] for h in b["hooks"]
    ]
    assert "atlas agent-log session-end" in session_end_commands
    assert HOOK_COMMAND in session_end_commands


def test_install_rerun_is_a_no_op(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    hooks.install(settings)
    before = settings.read_text()

    added = hooks.install(settings)

    assert not any(added.values())
    assert settings.read_text() == before


def test_backup_only_created_when_original_file_existed(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"

    hooks.install(settings)  # nothing to back up yet — file didn't exist
    assert list(tmp_path.glob("settings.json.bak-*")) == []

    hooks.install(settings)  # file now exists — rerun backs it up before writing
    assert len(list(tmp_path.glob("settings.json.bak-*"))) == 1
