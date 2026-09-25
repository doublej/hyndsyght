"""Categorization rules: a hardcoded template TOML, read via tomllib.

Round-tripped through `add_pattern` / `remove_pattern` only — those are the
sole writers, and they rewrite the whole file atomically. Everything else
about the file (comments the user adds by hand, formatting) is not preserved
across a round-trip; only the header comment, [redact], [away],
[categories] and [clients] are.
"""

import hashlib
import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hyndsyght import paths

HEADER = """\
# hyndsyght categorization rules
#
# [redact.patterns] are regexes matched against window/app titles. A match
# keeps the row but stores no title (password managers, banking, anything
# private) — the time still counts, just without what it says.
#
# [away.patterns] are regexes for a title that means the machine is not in
# use at all (the lock screen): the row is dropped, like AFK.
#
# [categories] maps a dot-separated category path to a list of regexes.
# When multiple categories match the same title, the deepest path wins
# (e.g. "dev.browser" beats "dev").
#
# [clients] maps a dot-separated client path to a list of regexes, matched
# on their own against the title, the app and the project path under ~/dev
# (e.g. "python/finances"). A row gets a client and a category side by side.
# The deepest client path wins; equal depth goes to file order."""

TEMPLATE = f"""\
{HEADER}

[redact]
patterns = [
    "1Password",
    "Bitwarden",
]

[away]
patterns = [
    "^loginwindow$",  # the lock screen: time there is not activity
    "^ScreenSaverEngine$",
]

[categories]
"dev" = ["Terminal", "iTerm", "Code", "PyCharm", "Xcode"]
"dev.browser" = ["Chrome", "Safari", "Firefox", "Arc"]
"communication" = ["Slack", "Mail", "Messages", "Discord"]
"media" = ["Spotify", "Music", "YouTube"]

[clients]
"""


class InvalidPatternError(ValueError):
    """A submitted pattern does not compile as a regex."""


class UnknownCategoryError(ValueError):
    """A submitted category name has no patterns in the rules file."""


@dataclass(frozen=True)
class Rules:
    file_hash: str
    redact_patterns: tuple[re.Pattern[str], ...]
    away_patterns: tuple[re.Pattern[str], ...]
    categories: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...]
    clients: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = ()


def ensure_default(rules_path: Path | None = None) -> None:
    path = rules_path or paths.rules_path()
    if not path.exists():
        path.write_text(TEMPLATE)


def load_rules(rules_path: Path | None = None) -> Rules:
    path = rules_path or paths.rules_path()
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode())
    redact_patterns = tuple(
        re.compile(p) for p in data.get("redact", {}).get("patterns", [])
    )
    away_patterns = tuple(
        re.compile(p) for p in data.get("away", {}).get("patterns", [])
    )
    return Rules(
        file_hash=hashlib.sha256(raw).hexdigest(),
        redact_patterns=redact_patterns,
        away_patterns=away_patterns,
        categories=_compile_table(data.get("categories", {})),
        clients=_compile_table(data.get("clients", {})),
    )


def _compile_table(
    table: dict[str, list[str]],
) -> tuple[tuple[str, tuple[re.Pattern[str], ...]], ...]:
    return tuple(
        (name, tuple(re.compile(p) for p in patterns))
        for name, patterns in table.items()
    )


def add_pattern(category: str, pattern: str, rules_path: Path | None = None) -> Rules:
    """Adds `pattern` to `category`, creating it if new. Idempotent."""
    _validate_pattern(pattern)
    path = rules_path or paths.rules_path()
    data = tomllib.loads(path.read_text())
    patterns = data.setdefault("categories", {}).setdefault(category, [])
    if pattern not in patterns:
        patterns.append(pattern)
    _write_atomic(path, data)
    return load_rules(path)


def remove_pattern(
    category: str, pattern: str, rules_path: Path | None = None
) -> Rules:
    """Removes `pattern` from `category`. Removes the category if it is left empty."""
    path = rules_path or paths.rules_path()
    data = tomllib.loads(path.read_text())
    categories = data.setdefault("categories", {})
    if category not in categories:
        raise UnknownCategoryError(f"No category named {category!r}.")
    remaining = [p for p in categories[category] if p != pattern]
    if remaining:
        categories[category] = remaining
    else:
        del categories[category]
    _write_atomic(path, data)
    return load_rules(path)


def _validate_pattern(pattern: str) -> None:
    try:
        re.compile(pattern)
    except re.error as exc:
        raise InvalidPatternError(f"{pattern!r} is not a valid pattern: {exc}") from exc


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(_serialize(data))
    os.replace(tmp_path, path)


def _serialize(data: dict[str, Any]) -> str:
    redact_patterns: list[str] = data.get("redact", {}).get("patterns", [])
    away_patterns: list[str] = data.get("away", {}).get("patterns", [])
    redact_lines = "\n".join(f"    {json.dumps(p)}," for p in redact_patterns)
    away_lines = "\n".join(f"    {json.dumps(p)}," for p in away_patterns)
    return (
        f"{HEADER}\n\n[redact]\npatterns = [\n{redact_lines}\n]\n\n"
        f"[away]\npatterns = [\n{away_lines}\n]\n\n"
        f"[categories]\n{_table_lines(data.get('categories', {}))}\n\n"
        f"[clients]\n{_table_lines(data.get('clients', {}))}\n"
    )


def _table_lines(table: dict[str, list[str]]) -> str:
    return "\n".join(
        f"{json.dumps(name)} = [{', '.join(json.dumps(p) for p in patterns)}]"
        for name, patterns in table.items()
    )
