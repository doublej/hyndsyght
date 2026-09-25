from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hyndsyght.api.app import create_app
from hyndsyght.categorize import rules as rules_module
from hyndsyght.store.db import init_db


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db()
    rules_module.ensure_default()
    return TestClient(create_app(port=8420), base_url="http://127.0.0.1:8420")


@pytest.fixture
def auth_headers(tmp_path: Path, client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {(tmp_path / 'api-token').read_text().strip()}"}
