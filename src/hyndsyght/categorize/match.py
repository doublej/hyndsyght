"""Read-time categorization — cosmetic, so it's memoized rather than fail-closed.

Cache key includes the rules file's content hash, so editing rules
naturally invalidates stale entries without any explicit cache-clear. `extra`
(e.g. a media event's app name, or an agent event's cwd) is part of the key too —
it changes what can match, so two events differing only in `extra` must not
share a cache entry.
"""

import re

from hyndsyght.categorize.rules import Rules

UNCATEGORIZED = "uncategorized"

_cache: dict[tuple[str, str, str, str], str] = {}


def categorize(
    title: str | None, kind: str, rules: Rules, extra: str | None = None
) -> str:
    key = (title or "", extra or "", kind, rules.file_hash)
    if key not in _cache:
        _cache[key] = _deepest(rules.categories, title, extra) or UNCATEGORIZED
    return _cache[key]


_client_cache: dict[tuple[str, str, str, str], str | None] = {}


def client_of(
    title: str | None,
    rules: Rules,
    extra: str | None = None,
    project: str | None = None,
) -> str | None:
    """The client from `[clients]`, matched on its own: title, app/cwd, then project."""
    key = (title or "", extra or "", project or "", rules.file_hash)
    if key not in _client_cache:
        _client_cache[key] = _deepest(rules.clients, *key[:3])
    return _client_cache[key]


def _deepest(
    table: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...], *texts: str | None
) -> str | None:
    """The deepest name whose patterns match any text; equal depth goes to file order."""
    matches = [
        name
        for name, patterns in table
        if any(text and p.search(text) for p in patterns for text in texts)
    ]
    return max(matches, key=lambda name: name.count("."), default=None)


def payload_match_field(payload: dict[str, object]) -> str | None:
    """The one payload field, if any, worth matching rules against.

    `title` alone identifies `window` (title is the app name already) and
    `afk`/`agent`-close events (nothing to match). `media`'s title is a track
    name, so its app lives in `payload["app"]`; `agent`-open events carry no
    title at all, so their project lives in `payload["cwd"]`. Never both on
    the same row, so a plain preference order is enough.
    """
    app = payload.get("app")
    if isinstance(app, str):
        return app
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) else None
