import sqlite3
from itertools import chain, repeat
from pathlib import Path

import pytest

from hyndsyght import daemon
from hyndsyght.categorize.rules import load_rules
from hyndsyght.daemon import (
    SourceState,
    acquire_lock,
    apply_poll,
    redact_event,
    release_lock,
)
from hyndsyght.platform.types import Event


def test_acquire_lock_refuses_when_already_held(tmp_path: Path) -> None:
    lock_path = tmp_path / "daemon.lock"
    fd = acquire_lock(lock_path)
    assert fd is not None
    assert acquire_lock(lock_path) is None
    release_lock(fd)
    fd2 = acquire_lock(lock_path)
    assert fd2 is not None
    release_lock(fd2)


def test_apply_poll_opens_a_new_interval_on_first_event(
    conn: sqlite3.Connection,
) -> None:
    state = SourceState()
    apply_poll(conn, "window", state, Event(kind="window", title="Terminal"), now=1.0)
    rows = conn.execute(
        "SELECT source, kind, title, ts_start, ts_end FROM raw_events"
    ).fetchall()
    assert rows == [("window", "window", "Terminal", 1.0, 1.0)]
    assert state.row_id is not None


def test_apply_poll_closes_and_opens_on_state_change(conn: sqlite3.Connection) -> None:
    state = SourceState()
    apply_poll(conn, "window", state, Event(kind="window", title="Terminal"), now=1.0)
    apply_poll(conn, "window", state, Event(kind="window", title="Editor"), now=5.0)
    rows = conn.execute(
        "SELECT title, ts_start, ts_end FROM raw_events ORDER BY ts_start"
    ).fetchall()
    assert rows == [("Terminal", 1.0, 5.0), ("Editor", 5.0, 5.0)]


def test_apply_poll_only_refreshes_ts_end_when_unchanged(
    conn: sqlite3.Connection,
) -> None:
    state = SourceState()
    apply_poll(conn, "window", state, Event(kind="window", title="Terminal"), now=1.0)
    apply_poll(
        conn, "window", state, Event(kind="window", title="Terminal"), now=2.0
    )  # too soon to refresh
    rows = conn.execute("SELECT ts_start, ts_end FROM raw_events").fetchall()
    assert rows == [(1.0, 1.0)]


def test_apply_poll_backdates_the_open_when_open_at_given(
    conn: sqlite3.Connection,
) -> None:
    state = SourceState()
    apply_poll(conn, "afk", state, Event(kind="active", title=None), now=1.0)
    apply_poll(
        conn, "afk", state, Event(kind="afk", title=None), now=310.0, open_at=300.0
    )
    rows = conn.execute(
        "SELECT kind, ts_start, ts_end FROM raw_events ORDER BY ts_start"
    ).fetchall()
    assert rows == [("active", 1.0, 300.0), ("afk", 300.0, 310.0)]


def test_apply_poll_closes_interval_when_event_becomes_none(
    conn: sqlite3.Connection,
) -> None:
    state = SourceState()
    apply_poll(conn, "media", state, Event(kind="playing", title="Track"), now=1.0)
    apply_poll(conn, "media", state, None, now=5.0)
    rows = conn.execute("SELECT ts_end FROM raw_events").fetchall()
    assert rows == [(5.0,)]
    assert state.row_id is None


def test_redact_event_drops_away_titles_like_afk(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text('[away]\npatterns = ["^loginwindow$"]\n\n[redact]\npatterns = []\n')
    rules = load_rules(path)
    locked = Event(kind="window", title="loginwindow", payload={"app": "loginwindow"})
    assert redact_event(locked, rules) is None


def test_redact_event_wipes_the_title_but_keeps_the_row(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text('[redact]\npatterns = ["1Password"]\n\n[away]\npatterns = []\n')
    rules = load_rules(path)
    vault = Event(kind="window", title="Personal", payload={"app": "1Password"})
    titled = Event(kind="window", title="1Password - Login", payload={"app": "Chrome"})
    for event in (vault, titled):
        result = redact_event(event, rules)
        assert result is not None
        assert result.title is None
        assert result.payload is not None
        assert result.payload["redacted"] is True


def test_redact_event_passes_through_an_unmatched_title(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text("[redact]\npatterns = []\n\n[away]\npatterns = []\n")
    rules = load_rules(path)
    other = Event(kind="window", title="Inbox", payload={"app": "Chrome"})
    assert redact_event(other, rules) is other


def test_pause_file_round_trips(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    assert daemon.paused_until() == 0.0
    daemon.set_pause(123.5)
    assert daemon.paused_until() == 123.5
    daemon.set_pause(float("inf"))
    assert daemon.paused_until() == float("inf")
    daemon.set_pause(None)
    assert daemon.paused_until() == 0.0


class _Watcher:
    def __init__(self, event: Event | None) -> None:
        self.event = event

    def poll(self) -> Event | None:
        return self.event


class _StopLoop(Exception):
    pass


def test_paused_tick_closes_the_window_row_and_writes_nothing_new(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    window = Event(kind="window", title="Editor", payload={"app": "Code"})
    monkeypatch.setattr(daemon.platform, "afk_watcher", lambda: _Watcher(None))
    monkeypatch.setattr(daemon.platform, "window_watcher", lambda: _Watcher(window))
    monkeypatch.setattr(daemon.platform, "media_watcher", lambda: _Watcher(None))
    sleeps = iter([lambda: daemon.set_pause(float("inf")), None])

    def fake_sleep(_: float) -> None:
        pause = next(sleeps)
        if pause is None:
            raise _StopLoop
        pause()

    monkeypatch.setattr(daemon.time, "sleep", fake_sleep)
    with pytest.raises(_StopLoop):
        daemon._run_loop(once=False)
    rows = conn.execute("SELECT title, ts_end > ts_start FROM raw_events").fetchall()
    assert rows == [("Editor", 1)]


def test_a_tick_gap_past_sleep_closes_open_rows_at_the_last_tick(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    window = Event(kind="window", title="Editor", payload={"app": "Code"})
    monkeypatch.setattr(daemon.platform, "afk_watcher", lambda: _Watcher(None))
    monkeypatch.setattr(daemon.platform, "window_watcher", lambda: _Watcher(window))
    monkeypatch.setattr(daemon.platform, "media_watcher", lambda: _Watcher(None))
    gap_tick = 1.0 + 2 * 3600
    # last_tick init, tick 1, tick 2 (2h gap), then hold — other code (e.g.
    # write_interval's created_at) also calls time.time() within a tick.
    times = chain([1.0, 1.0, gap_tick], repeat(gap_tick))
    monkeypatch.setattr(daemon.time, "time", lambda: next(times))
    sleeps = iter([lambda: None, None])

    def fake_sleep(_: float) -> None:
        action = next(sleeps)
        if action is None:
            raise _StopLoop
        action()

    monkeypatch.setattr(daemon.time, "sleep", fake_sleep)
    with pytest.raises(_StopLoop):
        daemon._run_loop(once=False)
    rows = conn.execute(
        "SELECT ts_start, ts_end FROM raw_events WHERE source = 'window' ORDER BY ts_start"
    ).fetchall()
    assert rows == [(1.0, 1.0), (gap_tick, gap_tick)]
