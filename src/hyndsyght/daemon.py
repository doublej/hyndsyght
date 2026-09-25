"""The one background process: baseline watchers + agent-event ingest + reap,
one singleton lock, one writer connection, per-source polling cadence.
"""

import fcntl
import sqlite3
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO

from hyndsyght import paths, platform
from hyndsyght.agentwatch import ingest, reaper
from hyndsyght.categorize.exclude import is_away, should_redact
from hyndsyght.categorize.rules import Rules, ensure_default, load_rules
from hyndsyght.platform.types import Event
from hyndsyght.store import db, events

AFK_POLL_SECONDS = 3.0
MEDIA_POLL_SECONDS = 12.0
MEDIA_POLL_SECONDS_AFK = 30.0
REFRESH_SECONDS = 20.0
INGEST_SECONDS = 7.0
REAP_SECONDS = 300.0
TICK_SECONDS = AFK_POLL_SECONDS
TICK_GAP_FACTOR = 3


def acquire_lock(lock_path: Path) -> IO[str] | None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = lock_path.open("w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fd.close()
        return None
    return fd


def release_lock(fd: IO[str]) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()


@dataclass
class SourceState:
    row_id: int | None = None
    kind: str | None = None
    title: str | None = None
    last_refresh: float = 0.0


def apply_poll(
    conn: sqlite3.Connection,
    source: str,
    state: SourceState,
    event: Event | None,
    now: float,
    *,
    open_at: float | None = None,
) -> None:
    """Close/open on state change; otherwise only periodically refresh ts_end.

    `open_at` backdates the transition point (close of the old row, start of
    the new one) when it differs from `now` — e.g. AFK's start is the moment
    the user went idle, not the moment the daemon noticed.
    """
    if event is None:
        if state.row_id is not None:
            events.update_interval_end(conn, state.row_id, now)
            state.row_id = state.kind = state.title = None
        return
    if state.row_id is None or (event.kind, event.title) != (state.kind, state.title):
        transition_at = open_at if open_at is not None else now
        if state.row_id is not None:
            events.update_interval_end(conn, state.row_id, transition_at)
        state.row_id = events.write_interval(
            conn,
            source=source,
            kind=event.kind,
            title=event.title,
            ts_start=transition_at,
            ts_end=now,
            payload=event.payload,
        )
        state.kind, state.title, state.last_refresh = event.kind, event.title, now
        return
    if now - state.last_refresh >= REFRESH_SECONDS:
        events.update_interval_end(conn, state.row_id, now)
        state.last_refresh = now


def close_open_rows(conn: sqlite3.Connection, ts: float, *states: SourceState) -> None:
    """Close every currently open row at `ts` — used after a sleep/tick gap,
    so the row ends where we last know things were fine, not where we
    noticed the gap."""
    for state in states:
        if state.row_id is not None:
            events.update_interval_end(conn, state.row_id, ts)
            state.row_id = state.kind = state.title = None


def redact_event(event: Event | None, rules: Rules) -> Event | None:
    """Away drops the event like AFK; redact keeps the row but wipes the title."""
    if event is None:
        return None
    app = (event.payload or {}).get("app")
    if is_away(event.title, rules) or is_away(app, rules):
        return None
    if should_redact(event.title, rules) or should_redact(app, rules):
        payload = {**(event.payload or {}), "redacted": True}
        return replace(event, title=None, payload=payload)
    return event


def paused_until() -> float:
    """Epoch seconds window/media capture is paused until; inf = until resumed."""
    path = paths.pause_path()
    return float(path.read_text()) if path.exists() else 0.0


def set_pause(until: float | None) -> None:
    if until is None:
        paths.pause_path().unlink(missing_ok=True)
        return
    paths.pause_path().write_text(str(until))


def run_forever(*, once: bool = False) -> None:
    lock_fd = acquire_lock(paths.lock_path())
    if lock_fd is None:
        raise SystemExit("hyndsyght daemon is already running.")
    try:
        _run_loop(once=once)
    finally:
        release_lock(lock_fd)


def _run_loop(*, once: bool) -> None:
    conn = db.connect(paths.db_path())
    ensure_default()
    afk_watcher, window_watcher, media_watcher = (
        platform.afk_watcher(),
        platform.window_watcher(),
        platform.media_watcher(),
    )
    afk_state, window_state, media_state = SourceState(), SourceState(), SourceState()
    last = dict.fromkeys(("afk", "media", "ingest", "reap"), 0.0)
    is_afk = False
    last_tick = time.time()

    while True:
        now = time.time()
        rules = load_rules()  # re-read each tick so exclude edits apply at once
        paused = now < paused_until()
        afk_backdate: float | None = None
        with conn:
            if now - last_tick > TICK_GAP_FACTOR * TICK_SECONDS:
                # Sleep or a stalled tick: close what was open where we last
                # know it was fine, instead of stretching it across the gap.
                close_open_rows(conn, last_tick, afk_state, window_state, media_state)
            last_tick = now

            if now - last["afk"] >= AFK_POLL_SECONDS:
                last["afk"] = now
                afk_event = afk_watcher.poll()
                was_afk, is_afk = (
                    is_afk,
                    (afk_event is not None and afk_event.kind == "afk"),
                )
                if is_afk and not was_afk and afk_event is not None:
                    idle = (afk_event.payload or {}).get("idle_seconds", 0.0)
                    afk_backdate = now - idle
                apply_poll(conn, "afk", afk_state, afk_event, now, open_at=afk_backdate)

            # Close the window row on AFK, or the return to the same window
            # stretches it across the whole absence. Pause closes it the same
            # way. Went-idle backdates the close to when AFK actually started.
            window_event = None if is_afk or paused else window_watcher.poll()
            window_event = redact_event(window_event, rules)
            window_now = afk_backdate if afk_backdate is not None else now
            apply_poll(conn, "window", window_state, window_event, window_now)

            media_interval = MEDIA_POLL_SECONDS_AFK if is_afk else MEDIA_POLL_SECONDS
            if now - last["media"] >= media_interval:
                last["media"] = now
                media_event = None if paused else media_watcher.poll()
                media_event = redact_event(media_event, rules)
                apply_poll(conn, "media", media_state, media_event, now)

            if now - last["ingest"] >= INGEST_SECONDS:
                last["ingest"] = now
                ingest.ingest(conn)

            if now - last["reap"] >= REAP_SECONDS:
                last["reap"] = now
                reaper.reap(conn, now)

        if once:
            return
        time.sleep(TICK_SECONDS)
