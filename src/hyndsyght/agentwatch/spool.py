"""Append-only spool + offset-tracked tail reader.

Mirrors aw-watcher-agents/sources.py's incremental read_new_lines() pattern:
the offset is a separate sidecar file, not touched until the caller has
durably applied what it read.
"""

import json
from pathlib import Path
from typing import Any


def append(payload: dict[str, Any], spool_path: Path) -> None:
    spool_path.parent.mkdir(parents=True, exist_ok=True)
    with spool_path.open("a") as f:
        f.write(json.dumps(payload) + "\n")


def _offset_path(spool_path: Path) -> Path:
    return spool_path.with_name(spool_path.name + ".offset")


def read_offset(spool_path: Path) -> int:
    offset_path = _offset_path(spool_path)
    if not offset_path.exists():
        return 0
    return int(offset_path.read_text())


def write_offset(spool_path: Path, offset: int) -> None:
    _offset_path(spool_path).write_text(str(offset))


def read_new_lines(spool_path: Path) -> tuple[list[str], int]:
    """Lines appended since the persisted offset, and the offset to persist after committing them."""
    start = read_offset(spool_path)
    if not spool_path.exists():
        return [], start
    if spool_path.stat().st_size < start:
        start = 0  # ponytail: a truncated/rotated spool re-reads from scratch.
    lines = []
    pos = start
    with spool_path.open("rb") as fh:
        fh.seek(start)
        for raw in fh:
            if not raw.endswith(b"\n"):
                break  # partial write; next run picks it up
            pos += len(raw)
            lines.append(raw.decode("utf-8", "replace"))
    return lines, pos
