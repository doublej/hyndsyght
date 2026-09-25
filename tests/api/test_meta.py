from pathlib import Path

from fastapi.testclient import TestClient

from hyndsyght.store.db import connect
from hyndsyght.store.events import open_or_close_agent_event


def test_status_report_shape(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/status", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "daemon_running" in body
    assert "hooks_registered_count" in body


def test_rules_summary_reflects_default_template(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/rules", headers=auth_headers)
    body = resp.json()
    names = {entry["name"] for entry in body["categories"]}
    assert "dev" in names
    assert "1Password" in body["redact_patterns"]
    assert "^loginwindow$" in body["away_patterns"]


def test_categorize_preview_matches_redacts_and_leaves_away(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/categorize?title=iTerm", headers=auth_headers)
    assert resp.json() == {"away": False, "redacted": False, "category": "dev"}

    resp = client.get("/api/categorize?title=1Password", headers=auth_headers)
    assert resp.json() == {"away": False, "redacted": True, "category": None}

    resp = client.get("/api/categorize?title=loginwindow", headers=auth_headers)
    assert resp.json() == {"away": True, "redacted": False, "category": None}


def test_rules_post_adds_pattern_and_returns_summary(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/rules",
        json={"category": "dev", "pattern": "Ghostty"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    dev = next(c for c in resp.json()["categories"] if c["name"] == "dev")
    assert "Ghostty" in dev["patterns"]


def test_rules_post_bad_regex_is_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/rules",
        json={"category": "dev", "pattern": "[unclosed"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_rules_delete_removes_pattern(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.request(
        "DELETE",
        "/api/rules",
        json={"category": "dev", "pattern": "Terminal"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    dev = next(c for c in resp.json()["categories"] if c["name"] == "dev")
    assert "Terminal" not in dev["patterns"]


def test_rules_delete_unknown_category_is_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.request(
        "DELETE",
        "/api/rules",
        json={"category": "nonexistent", "pattern": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_rules_post_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/rules", json={"category": "dev", "pattern": "X"})
    assert resp.status_code == 401


def test_rules_delete_requires_auth(client: TestClient) -> None:
    resp = client.request(
        "DELETE", "/api/rules", json={"category": "dev", "pattern": "Terminal"}
    )
    assert resp.status_code == 401


def test_sessions_rolls_up_turns_and_subagents(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn = connect(tmp_path / "hyndsyght.db")
    with conn:
        open_or_close_agent_event(
            conn,
            event_uid="agent-turn:sess-1:prompt-1",
            ts=1.0,
            kind="claude-code-turn",
            title=None,
            payload={"session_id": "sess-1"},
            closing=False,
        )
        open_or_close_agent_event(
            conn,
            event_uid="agent-turn:sess-1:prompt-1",
            ts=5.0,
            kind="claude-code-turn",
            title=None,
            payload={"intent": "Wrote the plan."},
            closing=True,
        )
        open_or_close_agent_event(
            conn,
            event_uid="agent-subagent:sess-1:agent-1",
            ts=2.0,
            kind="claude-code-subagent",
            title="general-purpose",
            payload={"session_id": "sess-1", "agent_type": "general-purpose"},
            closing=False,
        )
        open_or_close_agent_event(
            conn,
            event_uid="agent-subagent:sess-1:agent-1",
            ts=4.0,
            kind="claude-code-subagent",
            title="general-purpose",
            payload={"intent": "Explored the code."},
            closing=True,
        )
    conn.close()

    resp = client.get("/api/sessions", headers=auth_headers)
    body = resp.json()
    assert len(body) == 1
    assert body[0]["session_id"] == "sess-1"
    assert body[0]["turns"] == 1
    assert body[0]["subagents"] == 1
    assert body[0]["last_intent"] == "Wrote the plan."
