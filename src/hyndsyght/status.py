"""`hyndsyght status` — daemon/hook/DB health, read-only."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from hyndsyght import paths
from hyndsyght.daemon import acquire_lock, release_lock

REQUIRED_HOOKS = (
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "SubagentStart",
    "SubagentStop",
    "SessionEnd",
)
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
HOOK_COMMAND = "hyndsyght agent-event record"
SCREEN_RECORDING_PANE_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
)
WINDOW_TITLE_LOOKBACK_SECONDS = 3600.0


def report() -> dict[str, Any]:
    hooks_present, hooks_total = _hooks_registered_count(CLAUDE_SETTINGS_PATH)
    return {
        "daemon_running": _daemon_running(),
        "db_size_bytes": paths.db_path().stat().st_size
        if paths.db_path().exists()
        else 0,
        "last_event_per_source": _last_event_per_source(),
        "hooks_registered": hooks_present == hooks_total,
        "hooks_registered_count": [hooks_present, hooks_total],
        "window_titles_empty_last_hour": _window_titles_suspiciously_empty(),
    }


def render_human(data: dict[str, Any]) -> str:
    lines = [
        "✓ Daemon running"
        if data["daemon_running"]
        else "✗ Daemon not running — run `just service-install` or `hyndsyght daemon`"
    ]

    present, total = data["hooks_registered_count"]
    mark = "✓" if present == total else "✗"
    lines.append(f"{mark} Claude Code hooks installed ({present}/{total} events)")
    if present != total:
        lines.append("    → run `hyndsyght setup`")

    if data["window_titles_empty_last_hour"]:
        lines.append(
            "✗ Screen Recording permission — window titles look empty in the last hour"
        )
        lines.append("    → System Settings → Privacy & Security → Screen Recording")
        lines.append(f'    → or: open "{SCREEN_RECORDING_PANE_URL}"')
    else:
        lines.append("✓ Screen Recording permission looks OK")

    lines.append(f"✓ Database: {_human_size(data['db_size_bytes'])}")
    if data["last_event_per_source"]:
        now = time.time()
        ages = " · ".join(
            f"{source}: {_human_age(now - ts)} ago"
            for source, ts in sorted(data["last_event_per_source"].items())
        )
        lines.append(f"    last event — {ages}")

    lines.append("")
    lines.append("Run `hyndsyght serve` to view your dashboard.")
    return "\n".join(lines)


def _human_size(num_bytes: int) -> str:
    kb = num_bytes / 1024
    if kb < 1024:  # ponytail: KB/MB only, this is a local sqlite event log
        return f"{kb:.0f} KB"
    return f"{kb / 1024:.1f} MB"


def _human_age(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.0f}h"


def _daemon_running() -> bool:
    fd = acquire_lock(paths.lock_path())
    if fd is None:
        return True
    release_lock(fd)
    return False


def _last_event_per_source() -> dict[str, float]:
    if not paths.db_path().exists():
        return {}
    conn = sqlite3.connect(f"file:{paths.db_path()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT source, MAX(ts_start) FROM raw_events GROUP BY source"
        ).fetchall()
    finally:
        conn.close()
    return dict(rows)


def _hooks_registered_count(settings_path: Path) -> tuple[int, int]:
    if not settings_path.exists():
        return 0, len(REQUIRED_HOOKS)
    hooks = json.loads(settings_path.read_text()).get("hooks", {})
    present = sum(_event_has_hyndsyght(hooks.get(name, [])) for name in REQUIRED_HOOKS)
    return present, len(REQUIRED_HOOKS)


def _hooks_registered(settings_path: Path) -> bool:
    present, total = _hooks_registered_count(settings_path)
    return present == total


def _event_has_hyndsyght(entries: list[dict[str, Any]]) -> bool:
    return any(
        hook.get("command") == HOOK_COMMAND
        for block in entries
        for hook in block.get("hooks", [])
    )


def _window_titles_suspiciously_empty() -> bool:
    if not paths.db_path().exists():
        return False
    conn = sqlite3.connect(f"file:{paths.db_path()}?mode=ro", uri=True)
    try:
        cutoff = time.time() - WINDOW_TITLE_LOOKBACK_SECONDS
        rows = conn.execute(
            "SELECT title, json_extract(payload, '$.app') FROM raw_events "
            "WHERE source = 'window' AND ts_start >= ?",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    return bool(rows) and all(titles_missing(title, app) for title, app in rows)


def titles_missing(title: str | None, app: str | None) -> bool:
    """Without Screen Recording the watcher falls back to the app name.

    So a withheld title shows up as title == app, never as NULL. Checking for
    NULL alone made this always report the permission as fine.
    """
    return title is None or title == app
