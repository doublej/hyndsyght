import sqlite3
from pathlib import Path

import pytest

from hyndsyght.store.db import init_db
from hyndsyght.store.events import write_interval
from hyndsyght.store.query import interval_rows, run_sql


def test_run_sql_reads_rows(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    write_interval(
        conn, source="window", kind="app", title="Editor", ts_start=1.0, ts_end=2.0
    )
    conn.commit()
    conn.close()

    rows = run_sql("SELECT title FROM raw_events", db_path)
    assert rows == [{"title": "Editor"}]


def test_run_sql_is_write_proof(db_path: Path) -> None:
    with pytest.raises(sqlite3.OperationalError):
        run_sql(
            "INSERT INTO raw_events (source, kind, ts_start, created_at) VALUES ('x','y',1,1)",
            db_path,
        )


def test_interval_rows_filters_by_source_and_open_rows(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db()
    conn = sqlite3.connect(tmp_path / "hyndsyght.db")
    write_interval(
        conn, source="window", kind="app", title="A", ts_start=1.0, ts_end=2.0
    )
    write_interval(
        conn, source="agent", kind="turn", title=None, ts_start=1.0, ts_end=2.0
    )
    write_interval(
        conn, source="window", kind="app", title="open", ts_start=1.0, ts_end=None
    )
    conn.commit()
    conn.close()

    assert interval_rows("window", 0.0, 10.0) == [(1.0, 2.0)]
