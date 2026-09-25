"""ActivityWatch history -> `raw_events` window and afk rows.

ActivityWatch stores every title change as its own event, half of them under
two seconds. The daemon samples every tick, so an event shorter than one tick
folds into the row before it and same-window neighbours merge: imported history
gets the resolution hyndsyght records at, and no time goes missing.

Rows carry the event_uid `aw:<bucket>:<first event id>`. An import replaces the
bucket's earlier rows, so running it again is always safe, even after the rules
changed. It stops where hyndsyght's own window recording begins, so no minute is
imported twice.
"""

import json
import math
import sqlite3
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hyndsyght.categorize.rules import Rules
from hyndsyght.daemon import TICK_SECONDS, redact_event
from hyndsyght.platform.types import Event

# Watcher client -> hyndsyght source. Editor, Screen Time and other third-party
# buckets are left out: they are not the front window of this computer.
SOURCES = {"aw-watcher-window": "window", "aw-watcher-afk": "afk"}
DEFAULT_URL = "http://localhost:5600"
UID_PREFIX = "aw:"
IMPORTED = {"imported": "activitywatch"}
BATCH = 5000  # rows per transaction, so the daemon's own writes never wait long
PAGE_SECONDS = 30 * 86400  # one API request per month bounds memory on big buckets
INSERT = (
    "INSERT INTO raw_events (event_uid, ts_start, ts_end, source, kind, title,"
    " payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)

AwEvent = dict[str, Any]
Bucket = dict[str, Any]


class ApiSource:
    """A running aw-server, read through its REST API."""

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def buckets(self) -> dict[str, Bucket]:
        return self._get("/api/0/buckets/")  # type: ignore[no-any-return]

    def events(self, bucket_id: str, bucket: Bucket, until: float) -> Iterator[AwEvent]:
        """Oldest first, one page per month from the bucket's first event.

        `created` can't be the start: aw-server stamps it in local time labelled
        UTC, hours after the first event. `metadata.start` is that first event.
        """
        first = (bucket.get("metadata") or {}).get("start") or bucket["created"]
        start, last = _parse(first), min(until, time.time())
        path = f"/api/0/buckets/{urllib.parse.quote(bucket_id)}/events"
        while start < last:
            end = min(start + PAGE_SECONDS, last)
            page = self._get(path, start=_iso(start), end=_iso(end), limit=-1)
            yield from sorted(page, key=_start)
            start = end

    def _get(self, path: str, **params: Any) -> Any:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        with urllib.request.urlopen(
            f"{self.url}{path}{query}", timeout=120
        ) as response:
            return json.load(response)


class FileSource:
    """An ActivityWatch export: the JSON that aw-server's /api/0/export returns."""

    def __init__(self, path: Path) -> None:
        self.data: dict[str, Bucket] = json.loads(path.read_text())["buckets"]

    def buckets(self) -> dict[str, Bucket]:
        return self.data

    def events(self, bucket_id: str, bucket: Bucket, until: float) -> Iterator[AwEvent]:
        return iter(sorted(bucket.get("events", []), key=_start))


Source = ApiSource | FileSource


@dataclass
class Run:
    """One row to be: consecutive events in the same state."""

    uid: str
    start: float
    end: float
    event: Event


@dataclass(frozen=True)
class BucketResult:
    bucket_id: str
    rows: int
    hidden: int
    first: float | None
    last: float | None


def select_buckets(
    buckets: dict[str, Bucket], hosts: Iterable[str]
) -> dict[str, Bucket]:
    wanted = set(hosts)
    return {
        bucket_id: bucket
        for bucket_id, bucket in sorted(buckets.items())
        if bucket.get("client") in SOURCES
        and (not wanted or bucket.get("hostname") in wanted)
    }


def overview(buckets: dict[str, Bucket], conn: sqlite3.Connection) -> dict[str, Any]:
    """What an import would read, for the dashboard's wizard."""
    counts, until = imported_counts(conn), native_start(conn)
    chosen = select_buckets(buckets, ())
    return {
        "until": None if math.isinf(until) else until,
        "buckets": [_describe(bid, b, counts.get(bid, 0)) for bid, b in chosen.items()],
        "skipped": sorted(set(buckets) - set(chosen)),
        "imported_rows": sum(counts.values()),
    }


def imported_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Rows imported so far, per bucket: the part of `aw:<bucket>:<id>` before the id."""
    rows = conn.execute(
        "SELECT substr(event_uid, 4, instr(substr(event_uid, 4), ':') - 1), COUNT(*)"
        " FROM raw_events WHERE substr(event_uid, 1, 3) = ? GROUP BY 1",
        (UID_PREFIX,),
    ).fetchall()
    return dict(rows)


def native_start(conn: sqlite3.Connection) -> float:
    """Where hyndsyght's own window recording begins; inf when it never recorded."""
    (start,) = conn.execute(
        "SELECT MIN(ts_start) FROM raw_events"
        " WHERE source = 'window' AND event_uid IS NULL"
    ).fetchone()
    return float(start) if start is not None else math.inf


def import_bucket(
    conn: sqlite3.Connection,
    source: Source,
    bucket_id: str,
    bucket: Bucket,
    rules: Rules,
    until: float,
    *,
    write: bool,
) -> BucketResult:
    kind = SOURCES[bucket["client"]]
    to_event = _window_event if kind == "window" else _afk_event
    events = source.events(bucket_id, bucket, until)
    runs = list(merge(bucket_id, _items(events, to_event, rules, until)))
    if write:
        replace_bucket(conn, bucket_id, kind, runs)
    hidden = sum(1 for run in runs if (run.event.payload or {}).get("redacted"))
    first, last = (runs[0].start, runs[-1].end) if runs else (None, None)
    return BucketResult(bucket_id, len(runs), hidden, first, last)


def merge(
    bucket_id: str, items: Iterable[tuple[float, float, str, Event]]
) -> Iterator[Run]:
    """Same-state neighbours join; a blip shorter than one tick joins the row before it."""
    run: Run | None = None
    for start, end, event_id, event in items:
        touching = run is not None and start - run.end <= TICK_SECONDS
        if (
            run is not None
            and touching
            and (event == run.event or end - start < TICK_SECONDS)
        ):
            run.end = max(run.end, end)
            continue
        if run is not None and (run := _trimmed(run, start)) is not None:
            yield run
        run = Run(f"{UID_PREFIX}{bucket_id}:{event_id}", start, end, event)
    if run is not None:
        yield run


def replace_bucket(
    conn: sqlite3.Connection, bucket_id: str, source: str, runs: list[Run]
) -> None:
    """Swap the bucket's earlier import for `runs`. A rerun repairs an interrupted one."""
    prefix = f"{UID_PREFIX}{bucket_id}:"
    with conn:
        conn.execute(
            "DELETE FROM raw_events WHERE substr(event_uid, 1, ?) = ?",
            (len(prefix), prefix),
        )
    for i in range(0, len(runs), BATCH):
        with conn:
            conn.executemany(INSERT, [_row(run, source) for run in runs[i : i + BATCH]])


def remove_imported(conn: sqlite3.Connection) -> int:
    with conn:
        cursor = conn.execute(
            "DELETE FROM raw_events WHERE substr(event_uid, 1, ?) = ?",
            (len(UID_PREFIX), UID_PREFIX),
        )
    return cursor.rowcount


def _items(
    events: Iterable[AwEvent],
    to_event: Callable[[dict[str, Any], Rules], Event | None],
    rules: Rules,
    until: float,
) -> Iterator[tuple[float, float, str, Event]]:
    """(start, end, id, event) for each event before `until`, cut at `until`."""
    for aw_event in events:
        start = _start(aw_event)
        if start >= until:
            return
        end = min(start + aw_event["duration"], until)
        event = to_event(aw_event["data"], rules)
        if event is not None and end > start:
            yield start, end, str(aw_event.get("id", aw_event["timestamp"])), event


def _window_event(data: dict[str, Any], rules: Rules) -> Event | None:
    """What the daemon would have stored; None for away time such as the lock screen."""
    app = data["app"]
    payload = {"app": app, **IMPORTED}
    return redact_event(
        Event(kind="window", title=data.get("title") or app, payload=payload), rules
    )


def _afk_event(data: dict[str, Any], rules: Rules) -> Event | None:
    kind = {"not-afk": "active", "afk": "afk"}.get(data.get("status", ""))
    return Event(kind=kind, title=None, payload=IMPORTED) if kind else None


def _describe(bucket_id: str, bucket: Bucket, imported_rows: int) -> dict[str, Any]:
    metadata = bucket.get("metadata") or {}
    first, last = metadata.get("start"), metadata.get("end")
    return {
        "id": bucket_id,
        "host": bucket.get("hostname"),
        "source": SOURCES[bucket["client"]],
        "first": _parse(first) if first else None,
        "last": _parse(last) if last else None,
        "imported_rows": imported_rows,
    }


def _trimmed(run: Run, next_start: float) -> Run | None:
    """`run` cut where the next row starts, so rows of one source never overlap."""
    run.end = min(run.end, next_start)
    return run if run.end > run.start else None


def _row(run: Run, source: str) -> tuple[Any, ...]:
    payload = json.dumps(run.event.payload) if run.event.payload else None
    return (
        run.uid,
        run.start,
        run.end,
        source,
        run.event.kind,
        run.event.title,
        payload,
        time.time(),
    )


def _start(aw_event: AwEvent) -> float:
    return _parse(aw_event["timestamp"])


def _parse(timestamp: str) -> float:
    return datetime.fromisoformat(timestamp).timestamp()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).isoformat()
