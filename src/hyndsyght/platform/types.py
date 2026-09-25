"""Shared snapshot type returned by every platform watcher's poll()."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    kind: str
    title: str | None
    payload: dict[str, Any] | None = None
