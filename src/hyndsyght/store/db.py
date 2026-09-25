"""Connection helper and one-time DB initialization."""

import sqlite3
from pathlib import Path

from hyndsyght import paths
from hyndsyght.store.schema import init_schema


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(db_path: Path | None = None) -> None:
    path = db_path or paths.db_path()
    with connect(path) as conn:
        init_schema(conn)
