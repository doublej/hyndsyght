import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from hyndsyght.categorize.rules import load_rules
from hyndsyght.insights.activity import day_summary, load_spans
from hyndsyght.insights.intervals import day_bounds
from hyndsyght.store.db import connect
from hyndsyght.store.events import write_interval


def test_attention_summary_over_seeded_events(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        for i in range(3):  # three back-to-back 1s window intervals: 0-1, 1-2, 2-3
            write_interval(
                conn,
                source="window",
                kind="app",
                title=f"App {i}",
                ts_start=float(i),
                ts_end=float(i) + 1,
            )
    conn.close()

    resp = client.get("/api/attention?since=0&until=3600", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["longest_stretch_seconds"] == 3.0
    assert body["median_session_seconds"] == 3.0


def test_attention_category_filter(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn, source="window", kind="app", title="iTerm", ts_start=0.0, ts_end=60.0
        )
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Finder",
            ts_start=100.0,
            ts_end=110.0,
        )
    conn.close()

    resp = client.get(
        "/api/attention?since=0&until=3600&category=dev", headers=auth_headers
    )
    assert resp.json()["longest_stretch_seconds"] == 60.0


def test_ledger_summary_for_a_given_day(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    day_start = datetime(2024, 1, 15).astimezone().timestamp()  # DST-aware midnight
    with conn:
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Editor",
            ts_start=day_start,
            ts_end=day_start + 600,
        )
        write_interval(
            conn,
            source="agent",
            kind="claude-code-turn",
            title=None,
            ts_start=day_start,
            ts_end=day_start + 600,
        )
    conn.close()

    resp = client.get("/api/ledger?day=2024-01-15", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["human_minutes"] == 10.0
    assert body["agent_minutes"] == 10.0
    assert body["overlap_minutes"] == 10.0


def test_trend_returns_one_entry_per_day(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/trend?days=3", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert all("human_minutes" in day for day in body)


def test_trend_attention_metric(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/trend?metric=attention&days=2", headers=auth_headers)
    body = resp.json()
    assert len(body) == 2
    assert all("longest_stretch_seconds" in day for day in body)


def test_categories_breakdown_matches_media_via_payload_app(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    """Regression: media's title is a track name — the app that a media rule
    matches (e.g. "Spotify") only exists in payload.app."""
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="media",
            kind="playing",
            title="Benzo",
            ts_start=0.0,
            ts_end=60.0,
            payload={"app": "Spotify"},
        )
    conn.close()

    resp = client.get(
        "/api/categories?since=0&until=3600&source=media", headers=auth_headers
    )
    body = resp.json()
    media = next(entry for entry in body if entry["category"] == "media")
    assert media["seconds"] == 60.0


def test_categories_breakdown_sums_by_category(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn, source="window", kind="app", title="iTerm", ts_start=0.0, ts_end=60.0
        )
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Terminal",
            ts_start=60.0,
            ts_end=120.0,
        )
        write_interval(
            conn,
            source="window",
            kind="app",
            title="Finder",
            ts_start=200.0,
            ts_end=230.0,
        )
    conn.close()

    resp = client.get("/api/categories?since=0&until=3600", headers=auth_headers)
    body = resp.json()
    dev = next(entry for entry in body if entry["category"] == "dev")
    assert dev["seconds"] == 120.0


def test_day_clips_window_time_to_active_spans(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    day_start = datetime(2026, 1, 5).astimezone().timestamp()
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:  # one window row across 3h, but only 1h of it at the keyboard
        write_interval(
            conn,
            source="window",
            kind="window",
            title="iTerm2",
            ts_start=day_start + 3600,
            ts_end=day_start + 4 * 3600,
            payload={"app": "iTerm2"},
        )
        write_interval(
            conn,
            source="afk",
            kind="active",
            title=None,
            ts_start=day_start + 3600,
            ts_end=day_start + 7200,
        )
    conn.close()

    body = client.get("/api/day?day=2026-01-05", headers=auth_headers).json()
    assert body["active_seconds"] == 3600
    assert body["hours"][1] == 60.0 and sum(body["hours"]) == 60.0
    assert body["apps"] == [{"app": "iTerm2", "seconds": 3600}]
    assert body["break_seconds"] == 0


def test_short_row_across_midnight_counts_on_both_days(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    midnight = datetime(2026, 1, 6).astimezone().timestamp()
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:  # 23:30 → 00:30 at the keyboard; a stuck 30h row must not carry over
        for title, start, end in (
            ("iTerm2", midnight - 1800, midnight + 1800),
            ("Finder", midnight - 20 * 3600, midnight + 10 * 3600),
        ):
            write_interval(
                conn,
                source="window",
                kind="window",
                title=title,
                ts_start=start,
                ts_end=end,
                payload={"app": title},
            )
        write_interval(
            conn,
            source="afk",
            kind="active",
            title=None,
            ts_start=midnight - 3600,
            ts_end=midnight + 3600,
        )
    conn.close()

    spans = load_spans(day_bounds("2026-01-05")[0], day_bounds("2026-01-06")[1])
    for day in ("2026-01-05", "2026-01-06"):
        body = client.get(f"/api/day?day={day}", headers=auth_headers).json()
        ranged = day_summary(day, load_rules(), spans)
        assert body["active_seconds"] == ranged["active_seconds"]
        apps = {entry["app"]: entry["seconds"] for entry in body["apps"]}
        assert apps["iTerm2"] == 1800
        assert ("Finder" in apps) == (day == "2026-01-05")


def test_app_icon_uses_the_recorded_bundle(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    conn: sqlite3.Connection = connect(tmp_path / "hyndsyght.db")
    with conn:
        write_interval(
            conn,
            source="window",
            kind="window",
            title="Downloads",
            ts_start=0.0,
            ts_end=1.0,
            payload={
                "app": "Not Finder",
                "bundle": "/System/Library/CoreServices/Finder.app",
            },
        )
    conn.close()

    found = client.get("/api/app-icon?app=Not Finder", headers=auth_headers)
    missing = client.get("/api/app-icon?app=No Such App 9f2", headers=auth_headers)

    if sys.platform == "darwin":
        assert found.status_code == 200
        assert found.content.startswith(b"\x89PNG")
    assert missing.status_code == 404
