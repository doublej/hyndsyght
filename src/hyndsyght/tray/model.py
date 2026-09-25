"""What the menu-bar menu shows, computed without AppKit so it can be tested."""

import json
import time
from dataclasses import dataclass
from typing import NamedTuple

from hyndsyght import daemon
from hyndsyght import status as status_module
from hyndsyght.categorize.rules import load_rules
from hyndsyght.i18n import t
from hyndsyght.insights.activity import day_summary
from hyndsyght.store.query import run_sql

IDLE_AFTER_SECONDS = 60.0  # the daemon refreshes an open row's ts_end every 20s
MAX_ACTIVITY_CHARS = 50


@dataclass
class Snapshot:
    today_seconds: float
    activity: str | None  # None = idle
    daemon_running: bool
    permission_off: bool
    paused_until: float  # 0 = not paused, inf = until resumed


class Item(NamedTuple):
    label: str
    action: str | None = None
    enabled: bool = True
    children: tuple["Item", ...] = ()


SEPARATOR = Item("-", enabled=False)


def format_duration(seconds: float) -> str:
    hours, minutes = divmod(int(seconds // 60), 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def snapshot(now: float) -> Snapshot:
    report = status_module.report()
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    return Snapshot(
        today_seconds=day_summary(day, load_rules())["active_seconds"],
        activity=current_activity(now),
        daemon_running=report["daemon_running"],
        permission_off=report["window_titles_empty_last_hour"],
        paused_until=daemon.paused_until(),
    )


def current_activity(now: float) -> str | None:
    rows = run_sql(
        "SELECT title, payload, ts_end FROM raw_events WHERE source = 'window'"
        " ORDER BY ts_start DESC LIMIT 1"
    )
    if not rows or (rows[0]["ts_end"] or 0) < now - IDLE_AFTER_SECONDS:
        return None
    app = json.loads(rows[0]["payload"] or "{}").get("app")
    title = rows[0]["title"] or ""
    text = f"{app} · {title}" if app and title and app != title else app or title
    return _cut(text)


def _cut(text: str) -> str:
    return text if len(text) <= MAX_ACTIVITY_CHARS else text[:49] + "…"


def icon_name(daemon_running: bool, paused: bool) -> str:
    if not daemon_running:
        return "exclamationmark.triangle"
    return "pause.circle" if paused else "waveform.path"


def menu_items(snap: Snapshot, locale: str, now: float) -> list[Item]:
    items = [
        Item(
            t("tray.today", locale, time=format_duration(snap.today_seconds)),
            enabled=False,
        ),
        Item(_now_label(snap, locale, now), enabled=False),
    ]
    if not snap.daemon_running:
        items.append(Item(t("tray.daemon_down", locale), enabled=False))
    if snap.permission_off:
        items.append(Item(t("tray.permission_off", locale), "open_permission"))
    return [
        *items,
        SEPARATOR,
        *_controls(snap, locale, now),
        SEPARATOR,
        Item(t("tray.quit", locale), "quit"),
    ]


def _now_label(snap: Snapshot, locale: str, now: float) -> str:
    if now < snap.paused_until:
        if snap.paused_until == float("inf"):
            return t("tray.paused", locale)
        until = time.strftime("%H:%M", time.localtime(snap.paused_until))
        return t("tray.paused_until", locale, time=until)
    return t("tray.now", locale, activity=snap.activity or t("tray.idle", locale))


def _controls(snap: Snapshot, locale: str, now: float) -> list[Item]:
    pause = (
        Item(t("tray.resume", locale), "resume")
        if now < snap.paused_until
        else Item(
            t("tray.pause.title", locale),
            children=tuple(
                Item(t(f"tray.pause.{key}", locale), f"pause_{key}")
                for key in ("15m", "1h", "forever")
            ),
        )
    )
    return [
        Item(t("tray.open", locale), "open"),
        pause,
        Item(t("tray.restart_daemon", locale), "restart_daemon"),
    ]
