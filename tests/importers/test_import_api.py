"""/api/import/activitywatch, against a fake aw-server."""

import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hyndsyght.api.app import create_app
from hyndsyght.categorize import rules as rules_module
from hyndsyght.importers import activitywatch as aw
from hyndsyght.store.db import init_db

T0 = datetime(2026, 3, 2, 9, tzinfo=UTC)
WINDOW = "aw-watcher-window_desk.local"
AFK = "aw-watcher-afk_desk.local"


def _event(event_id: int, minute: int, seconds: float, **data: Any) -> dict[str, Any]:
    stamp = T0.replace(minute=minute).isoformat().replace("+00:00", "Z")
    return {"id": event_id, "timestamp": stamp, "duration": seconds, "data": data}


BUCKETS = {
    WINDOW: {
        "client": "aw-watcher-window",
        "hostname": "desk.local",
        "created": "2026-03-02T09:00:00Z",
        "metadata": {"start": "2026-03-02T09:00:00Z", "end": "2026-03-02T09:30:00Z"},
    },
    AFK: {
        "client": "aw-watcher-afk",
        "hostname": "desk.local",
        "created": "2026-03-02T09:00:00Z",
        "metadata": {"start": "2026-03-02T09:00:00Z", "end": "2026-03-02T09:30:00Z"},
    },
    "aw-watcher-pycharm_desk.local": {
        "client": "aw-watcher-pycharm",
        "hostname": "desk.local",
        "created": "2026-03-02T09:00:00Z",
    },
}
EVENTS = {
    WINDOW: [
        _event(1, 0, 600, app="iTerm2", title="✳ quiet-otter"),
        _event(2, 10, 1200, app="Google Chrome", title="Globex board"),
    ],
    AFK: [_event(3, 0, 1800, status="not-afk")],
}


def _fake_get(self: aw.ApiSource, path: str, **params: Any) -> Any:
    if path == "/api/0/buckets/":
        return BUCKETS
    bucket_id = path.split("/")[4]
    start, end = (
        datetime.fromisoformat(params[k]).timestamp() for k in ("start", "end")
    )
    return [e for e in EVENTS[bucket_id] if start <= aw._start(e) < end]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    monkeypatch.setattr(aw.ApiSource, "_get", _fake_get)
    init_db()
    rules_module.ensure_default()
    test_client = TestClient(create_app(port=8420), base_url="http://127.0.0.1:8420")
    token = (tmp_path / "api-token").read_text().strip()
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client


def test_overview_lists_window_and_afk_buckets(client: TestClient) -> None:
    body = client.get("/api/import/activitywatch").json()
    assert [b["id"] for b in body["buckets"]] == [AFK, WINDOW]
    assert body["buckets"][1]["host"] == "desk.local"
    assert body["buckets"][1]["first"] == T0.timestamp()
    assert body["skipped"] == ["aw-watcher-pycharm_desk.local"]
    assert body["until"] is None and body["imported_rows"] == 0


def test_import_a_bucket_then_remove_everything(client: TestClient) -> None:
    result = client.post("/api/import/activitywatch", json={"bucket": WINDOW}).json()
    assert result["rows"] == 2 and result["first"] == T0.timestamp()
    counts = {
        b["id"]: b["imported_rows"]
        for b in client.get("/api/import/activitywatch").json()["buckets"]
    }
    assert counts == {AFK: 0, WINDOW: 2}
    assert client.delete("/api/import/activitywatch").json() == {"removed": 2}


def test_only_window_and_afk_buckets_can_be_imported(client: TestClient) -> None:
    response = client.post(
        "/api/import/activitywatch", json={"bucket": "aw-watcher-pycharm_desk.local"}
    )
    assert response.status_code == 404


def test_bad_or_unreachable_address(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (
        client.get(
            "/api/import/activitywatch", params={"url": "file:///etc"}
        ).status_code
        == 400
    )

    def refuse(self: aw.ApiSource, path: str, **params: Any) -> Any:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(aw.ApiSource, "_get", refuse)
    response = client.get(
        "/api/import/activitywatch", params={"url": "http://127.0.0.1:9"}
    )
    assert response.status_code == 502
    assert (
        response.json()["detail"] == "Can't reach ActivityWatch at http://127.0.0.1:9."
    )
