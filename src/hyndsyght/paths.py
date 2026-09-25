"""Filesystem locations for hyndsyght's state (DB, rules, spool, token, lock)."""

from pathlib import Path

import click


def state_dir() -> Path:
    path = Path(click.get_app_dir("hyndsyght"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return state_dir() / "hyndsyght.db"


def rules_path() -> Path:
    return state_dir() / "rules.toml"


def spool_path() -> Path:
    return state_dir() / "agent-events.jsonl"


def token_path() -> Path:
    return state_dir() / "api-token"


def lock_path() -> Path:
    return state_dir() / "daemon.lock"


def pause_path() -> Path:
    return state_dir() / "paused-until"
