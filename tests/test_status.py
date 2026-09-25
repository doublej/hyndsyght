import json
from pathlib import Path
from typing import Any

from hyndsyght.status import (
    HOOK_COMMAND,
    REQUIRED_HOOKS,
    _hooks_registered,
    titles_missing,
)


def _hook_block(command: str) -> list[dict[str, Any]]:
    return [{"hooks": [{"type": "command", "command": command}]}]


def test_hooks_registered_false_when_keys_present_but_empty(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {name: [] for name in REQUIRED_HOOKS}}))
    assert _hooks_registered(settings) is False


def test_hooks_registered_false_when_missing_one(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"hooks": {name: _hook_block(HOOK_COMMAND) for name in REQUIRED_HOOKS[:-1]}}
        )
    )
    assert _hooks_registered(settings) is False


def test_hooks_registered_true_when_hyndsyght_command_present_for_all_six(
    tmp_path: Path,
) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"hooks": {name: _hook_block(HOOK_COMMAND) for name in REQUIRED_HOOKS}}
        )
    )
    assert _hooks_registered(settings) is True


def test_hooks_registered_false_when_only_another_tools_hook_present(
    tmp_path: Path,
) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"hooks": {name: _hook_block("other-tool run") for name in REQUIRED_HOOKS}}
        )
    )
    assert _hooks_registered(settings) is False


def test_hooks_registered_false_when_no_settings_file(tmp_path: Path) -> None:
    assert _hooks_registered(tmp_path / "missing.json") is False


def test_titles_missing_when_title_falls_back_to_app_name() -> None:
    assert titles_missing("Safari", "Safari") is True


def test_titles_missing_when_title_is_null() -> None:
    assert titles_missing(None, "Safari") is True


def test_titles_present_when_real_window_title_differs_from_app() -> None:
    assert titles_missing("Inbox — Safari", "Safari") is False
