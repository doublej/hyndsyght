import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from hyndsyght.store.db import connect
from hyndsyght.store.events import open_or_close_agent_event, write_interval


def _seed_window_events(tmp_path: Path, count: int) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        for i in range(count):
            write_interval(
                conn,
                source="window",
                kind="app",
                title=f"App {i}",
                ts_start=float(i),
                ts_end=float(i) + 1,
            )
    conn.close()


def test_valid_token_and_host_returns_events(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    _seed_window_events(tmp_path, 3)
    resp = client.get("/api/events", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_events_default_order_is_newest_first(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    _seed_window_events(tmp_path, 3)
    resp = client.get("/api/events", headers=auth_headers)
    titles = [row["title"] for row in resp.json()]
    assert titles == ["App 2", "App 1", "App 0"]


def test_before_id_paginates_older_rows(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    _seed_window_events(tmp_path, 3)
    first_page = client.get("/api/events?limit=1", headers=auth_headers).json()
    assert [row["title"] for row in first_page] == ["App 2"]

    next_page = client.get(
        f"/api/events?limit=1&before_id={first_page[0]['id']}", headers=auth_headers
    ).json()
    assert [row["title"] for row in next_page] == ["App 1"]


def test_events_limit_is_respected_and_capped_server_side(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    _seed_window_events(tmp_path, 3)
    resp = client.get("/api/events?limit=1", headers=auth_headers)
    assert len(resp.json()) == 1

    resp = client.get("/api/events?limit=999999", headers=auth_headers)
    assert resp.status_code == 200  # doesn't error; capped internally to MAX_LIMIT


def test_source_and_kind_filters(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn, source="window", kind="app", title="Editor", ts_start=1.0, ts_end=2.0
        )
        write_interval(
            conn, source="afk", kind="active", title=None, ts_start=1.0, ts_end=2.0
        )
    conn.close()

    resp = client.get("/api/events?source=afk", headers=auth_headers)
    assert [row["source"] for row in resp.json()] == ["afk"]

    resp = client.get("/api/events?kind=app", headers=auth_headers)
    assert [row["kind"] for row in resp.json()] == ["app"]


def test_q_filters_by_title_substring(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Terminal",
            ts_start=1.0,
            ts_end=2.0,
        )
        write_interval(
            conn, source="window", kind="app", title="Slack", ts_start=1.0, ts_end=2.0
        )
    conn.close()

    resp = client.get("/api/events?q=Term", headers=auth_headers)
    assert [row["title"] for row in resp.json()] == ["Terminal"]


def test_category_filter_matches_rules_toml(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn, source="window", kind="app", title="iTerm", ts_start=1.0, ts_end=2.0
        )
        write_interval(
            conn, source="window", kind="app", title="Finder", ts_start=1.0, ts_end=2.0
        )
    conn.close()
    with (tmp_path / "rules.toml").open("a") as rules_file:
        rules_file.write('"acme" = ["iTerm"]\n')  # the template ends in [clients]

    resp = client.get("/api/events?category=dev", headers=auth_headers)
    assert [row["title"] for row in resp.json()] == ["iTerm"]
    assert resp.json()[0]["client"] == "acme"


def test_session_filter_recovers_session_id_from_closed_turn(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    """Regression: open_or_close_agent_event replaces payload on close, so
    session_id must be recovered from event_uid, not from the closed payload."""
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        open_or_close_agent_event(
            conn,
            event_uid="agent-turn:sess-1:prompt-1",
            ts=1.0,
            kind="claude-code-turn",
            title=None,
            payload={"session_id": "sess-1", "cwd": "/tmp"},
            closing=False,
        )
        open_or_close_agent_event(
            conn,
            event_uid="agent-turn:sess-1:prompt-1",
            ts=2.0,
            kind="claude-code-turn",
            title=None,
            payload={"last_assistant_message": "Done.", "intent": "Fixed the bug."},
            closing=True,
        )
    conn.close()

    resp = client.get("/api/events?session=sess-1", headers=auth_headers)
    body = resp.json()
    assert len(body) == 1
    assert body[0]["session_id"] == "sess-1"
    assert body[0]["intent"] == "Fixed the bug."
