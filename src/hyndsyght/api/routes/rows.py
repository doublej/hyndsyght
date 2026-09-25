"""Shared row enrichment + param coercion for /api/events and /api/sessions."""

import json
from typing import Any

from hyndsyght.categorize.match import categorize, client_of, payload_match_field
from hyndsyght.categorize.rules import Rules
from hyndsyght.store.events import session_id_from_uid

MAX_LIMIT = 2000
DEFAULT_LIMIT = 200


def clamp_limit(limit: int) -> int:
    return min(max(limit, 1), MAX_LIMIT)


def enrich_rows(rows: list[dict[str, Any]], rules: Rules) -> list[dict[str, Any]]:
    """Adds category and client (read-time), session_id (recovered from event_uid), and intent."""
    for row in rows:
        payload = json.loads(row["payload"]) if row.get("payload") else {}
        extra = payload_match_field(payload)
        row["category"] = categorize(row.get("title"), row["kind"], rules, extra)
        row["client"] = client_of(row.get("title"), rules, extra)
        row["session_id"] = (
            session_id_from_uid(row.get("event_uid"))
            if row["source"] == "agent"
            else None
        )
        row["intent"] = payload.get("intent")
    return rows


def rollup_sessions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sessions: dict[str, dict[str, Any]] = {}
    for row in rows:
        session_id = row.get("session_id")
        if not session_id:
            continue
        session = sessions.setdefault(
            session_id,
            {
                "session_id": session_id,
                "turns": 0,
                "subagents": 0,
                "agent_minutes": 0.0,
                "last_intent": None,
                "last_ts": 0.0,
            },
        )
        if row["kind"] == "claude-code-turn":
            session["turns"] += 1
        elif row["kind"] == "claude-code-subagent":
            session["subagents"] += 1
        if row["ts_end"] is not None:
            session["agent_minutes"] += (row["ts_end"] - row["ts_start"]) / 60
        ts = row["ts_end"] or row["ts_start"]
        if ts >= session["last_ts"]:
            session["last_ts"] = ts
            if row.get("intent"):
                session["last_intent"] = row["intent"]
    return sorted(sessions.values(), key=lambda s: s["last_ts"], reverse=True)
