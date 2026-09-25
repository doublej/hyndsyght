"""The project of a human interval, borrowed from the agent working next to it.

A terminal's title is a session name ("✳ umber-weasel") that no agent row stores,
so the join is time overlap. The turn a prompt was submitted to during the window
row wins: that is the session the person typed into. Otherwise the turn that
overlaps the row longest wins.
"""

from pathlib import Path
from typing import Any

from hyndsyght.store.query import run_sql

TERMINAL_APPS = frozenset(
    {
        "iTerm2",
        "Terminal",
        "Ghostty",
        "WezTerm",
        "Alacritty",
        "kitty",
        "Warp",
        "cmux",
        "Code",
        "Cursor",
        "Zed",
        "PyCharm",
        "Xcode",
    }
)
# `~/Documents/development` is the retired symlink to `~/dev`; old rows carry it.
DEV_ROOTS = ("dev", "Documents/development")


def repo_path(cwd: str | None) -> str | None:
    """`~/dev/python/finances/src` -> `python/finances`; `None` outside the dev tree."""
    for root in DEV_ROOTS:
        prefix = f"{Path.home()}/{root}/"
        if cwd and cwd.startswith(prefix):
            parts = cwd.removeprefix(prefix).split("/")
            return "/".join(parts[:2]) if len(parts) > 1 and parts[1] else None
    return None


def agent_turns(start: float, end: float) -> list[dict[str, Any]]:
    """Closed agent rows with a `cwd` that overlap `[start, end)`."""
    return run_sql(
        "SELECT ts_start, ts_end, json_extract(payload, '$.cwd') AS cwd"
        " FROM raw_events WHERE source = 'agent' AND ts_end > ? AND ts_start < ?"
        " AND json_extract(payload, '$.cwd') IS NOT NULL",
        params=(start, end),
    )


def project_of(
    app: str | None, start: float, end: float, turns: list[dict[str, Any]]
) -> str | None:
    """The repo of the agent session behind a terminal or IDE row, else `None`."""
    if app not in TERMINAL_APPS:
        return None
    # ponytail: linear scan; callers pass one day's turns. Bisect if it gets slow.
    overlapping = [t for t in turns if t["ts_start"] < end and t["ts_end"] > start]
    best = max(
        overlapping,
        key=lambda t: (
            t["ts_start"] >= start,
            min(end, t["ts_end"]) - max(start, t["ts_start"]),
        ),
        default=None,
    )
    return repo_path(best["cwd"]) if best else None
