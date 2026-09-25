"""One fixture day, 2026-09-24, with every case the export must get right."""

from pathlib import Path

import pytest

from hyndsyght.categorize.rules import Rules, load_rules
from hyndsyght.insights.intervals import day_bounds
from hyndsyght.store.db import connect, init_db
from hyndsyght.store.events import write_interval

DAY, NEXT_DAY = "2026-09-24", "2026-09-25"
T0 = day_bounds(DAY)[0]
H = 3600.0

RULES = """\
[categories]
"dev" = ["iTerm"]
"dev.browser" = ["Chrome"]
"communication" = ["Mail"]
"business.ops.admin" = ["1Password"]
"private.admin.property" = ["Funda"]

[clients]
"acme.globex" = ["Globex"]
"initech" = ["^python/finances$"]
"""

WINDOWS = [
    # an AFK break from 10:00 to 10:30 cuts this to 2.5 h
    ("Globex board - Google Chrome", {"app": "Google Chrome"}, 9, 12),
    # a session name only: the project comes from the agent turn at 13:10
    ("✳ umber-weasel", {"app": "iTerm2"}, 13, 14),
    # redacted: the time stays, the title does not
    (None, {"app": "1Password", "redacted": True}, 14, 14.5),
    ("Funda - Safari", {"app": "Safari"}, 15, 16),  # private: left out
    ("Finder", {"app": "Finder"}, 16, 16.25),  # no rule: unclassified
    ("Inbox - Mail", {"app": "Mail"}, 23.5, 24.5),  # crosses midnight
]


def _write(conn, source, kind, title, start, end, payload=None) -> None:
    write_interval(
        conn,
        source=source,
        kind=kind,
        title=title,
        ts_start=T0 + start * H,
        ts_end=T0 + end * H,
        payload=payload,
    )


@pytest.fixture
def rules(tmp_path: Path, monkeypatch) -> Rules:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    init_db()
    (tmp_path / "rules.toml").write_text(RULES)
    with connect(tmp_path / "hyndsyght.db") as conn:
        _write(conn, "afk", "active", None, 9, 10)
        _write(conn, "afk", "active", None, 10.5, 25)
        for title, payload, start, end in WINDOWS:
            _write(conn, "window", "app", title, start, end, payload)
        cwd = {"cwd": f"{Path.home()}/dev/python/finances", "session_id": "s1"}
        _write(conn, "agent", "claude-code-turn", None, 13 + 1 / 6, 13.5 + 1 / 6, cwd)
    return load_rules(tmp_path / "rules.toml")
