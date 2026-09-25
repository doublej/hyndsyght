"""Idempotent, additive installer for hyndsyght's Claude Code lifecycle hooks.

Never overwrites another tool's hooks under the same event — appends to the
existing array instead. Backs up the settings file before any write.
"""

import json
import time
from pathlib import Path
from typing import Any

from hyndsyght.status import CLAUDE_SETTINGS_PATH, HOOK_COMMAND, REQUIRED_HOOKS


def install(settings_path: Path = CLAUDE_SETTINGS_PATH) -> dict[str, bool]:
    data: dict[str, Any] = (
        json.loads(settings_path.read_text()) if settings_path.exists() else {}
    )
    hooks = data.setdefault("hooks", {})
    if settings_path.exists():
        backup = settings_path.with_suffix(f".json.bak-{int(time.time())}")
        backup.write_text(settings_path.read_text())
    added = {event: _ensure_event(hooks, event) for event in REQUIRED_HOOKS}
    if any(added.values()):
        tmp = settings_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(settings_path)  # atomic
    return added


def _ensure_event(hooks: dict[str, Any], event: str) -> bool:
    entries = hooks.setdefault(event, [])
    if any(
        h.get("command") == HOOK_COMMAND for b in entries for h in b.get("hooks", [])
    ):
        return False
    entries.append({"hooks": [{"type": "command", "command": HOOK_COMMAND}]})
    return True
