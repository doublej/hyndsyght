import sqlite3
from pathlib import Path


def test_init_db_creates_table_and_pragmas(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "raw_events" in tables
