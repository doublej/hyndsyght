import sqlite3
from pathlib import Path

import pytest

from hyndsyght.store.db import init_db


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "hyndsyght.db"
    init_db(path)
    return path


@pytest.fixture
def conn(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)
