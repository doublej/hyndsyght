from pathlib import Path

from fastapi.testclient import TestClient

from hyndsyght.api.app import create_app


def test_wrong_host_header_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/events", headers={"Host": "evil.example.com", **auth_headers}
    )
    assert resp.status_code == 403


def test_missing_token_is_rejected(client: TestClient) -> None:
    resp = client.get("/api/events")
    assert resp.status_code == 401


def test_index_injects_token_into_placeholder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.api.app.STATIC_DIR", tmp_path / "static")
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "index.html").write_text(
        '<script>window.__HYNDSYGHT_TOKEN__ = "__HYNDSYGHT_TOKEN_PLACEHOLDER__";</script>'
    )
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    client = TestClient(create_app(port=8420), base_url="http://127.0.0.1:8420")

    resp = client.get("/")

    token = (tmp_path / "api-token").read_text().strip()
    assert f'window.__HYNDSYGHT_TOKEN__ = "{token}"' in resp.text
    assert "__HYNDSYGHT_TOKEN_PLACEHOLDER__" not in resp.text
