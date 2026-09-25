"""Latency budgets for the dashboard's heaviest reads, over a synthetic year.

ActivityWatch got slow as its history grew, not on day one. These fail when
hyndsyght starts down that road: a year of data, and the same routes the
dashboard calls.
"""

import json
import random
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hyndsyght.api.app import create_app
from hyndsyght.categorize import rules as rules_module
from hyndsyght.store.db import connect, init_db

DAYS = 365
WINDOW_ROWS_PER_DAY = 220  # ~80k/year; the live DB averages ~200/day
AGENT_ROWS_PER_DAY = 550  # ~200k/year; the live DB averages ~500/day
DAY_BUDGET_SECONDS = 0.1
STATS_BUDGET_SECONDS = 1.0
APPS = ["Code", "Google Chrome", "Ghostty", "Slack", "Finder", "Mail", "Figma"]


def _workday_rows(
    day_start: float, rng: random.Random
) -> tuple[list[tuple], list[tuple]]:
    """One day of window and AFK rows between 09:00 and ~19:00."""
    windows, afk = [], []
    ts = day_start + 9 * 3600
    for _ in range(WINDOW_ROWS_PER_DAY):
        length = rng.uniform(5, 300)
        app = rng.choice(APPS)
        payload = json.dumps({"app": app, "bundle": f"/Applications/{app}.app"})
        title = f"{app} — doc {rng.randrange(500)}"
        windows.append((ts, ts + length, "window", "app", title, payload, ts))
        ts += length
    afk.append((day_start + 9 * 3600, ts, "afk", "active", None, None, ts))
    afk.append((ts, day_start + 86400 + 9 * 3600, "afk", "afk", None, None, ts))
    return windows, afk


def _agent_rows(day_start: float, rng: random.Random) -> list[tuple]:
    rows = []
    for _ in range(AGENT_ROWS_PER_DAY):
        ts = day_start + rng.uniform(0, 86400)
        rows.append((ts, ts + rng.uniform(1, 600), "agent", "turn", None, None, ts))
    return rows


def _seed_year(db_path: Path) -> None:
    rng = random.Random(0)
    today_start = time.time() // 86400 * 86400
    rows: list[tuple] = []
    for offset in range(DAYS):
        day_start = today_start - offset * 86400
        windows, afk = _workday_rows(day_start, rng)
        rows += windows + afk + _agent_rows(day_start, rng)
    rows.sort(key=lambda row: (row[2], row[0]))  # index order: inserts append
    conn = connect(db_path)
    with conn:
        conn.executemany(
            "INSERT INTO raw_events (ts_start, ts_end, source, kind, title, payload,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    conn.close()


@pytest.fixture(scope="module")
def year_client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    state = tmp_path_factory.mktemp("year")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("hyndsyght.paths.state_dir", lambda: state)
        init_db()
        rules_module.ensure_default()
        _seed_year(state / "hyndsyght.db")
        client = TestClient(create_app(port=8420), base_url="http://127.0.0.1:8420")
        token = (state / "api-token").read_text().strip()
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


def _best_of_three(client: TestClient, url: str) -> float:
    """Fastest of three runs, so a busy machine doesn't fail the gate."""
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        assert client.get(url).status_code == 200
        timings.append(time.perf_counter() - started)
    return min(timings)


def test_day_stays_within_budget(year_client: TestClient) -> None:
    assert _best_of_three(year_client, "/api/day") < DAY_BUDGET_SECONDS


def test_year_of_stats_stays_within_budget(year_client: TestClient) -> None:
    elapsed = _best_of_three(year_client, "/api/stats?days=366")
    assert elapsed < STATS_BUDGET_SECONDS
