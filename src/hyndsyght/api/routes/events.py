"""GET /api/events — filtered, paginated, enriched raw_events feed."""

from typing import Any

from fastapi import APIRouter

from hyndsyght.api.routes.rows import DEFAULT_LIMIT, MAX_LIMIT, clamp_limit, enrich_rows
from hyndsyght.categorize.rules import load_rules
from hyndsyght.store.query import run_sql


def register_events_routes(router: APIRouter) -> None:
    @router.get("/api/events")
    def list_events(
        since: float | None = None,
        until: float | None = None,
        limit: int = DEFAULT_LIMIT,
        before_id: int | None = None,
        source: str | None = None,
        kind: str | None = None,
        category: str | None = None,
        session: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        needs_post_filter = category is not None or session is not None
        sql = "SELECT * FROM raw_events WHERE 1=1"
        params: list[Any] = []
        if before_id is not None:
            sql += " AND id < ?"
            params.append(before_id)
        if since is not None:
            sql += " AND ts_start >= ?"
            params.append(since)
        if until is not None:
            sql += " AND ts_start <= ?"
            params.append(until)
        if source is not None:
            sql += " AND source = ?"
            params.append(source)
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        if q is not None:
            sql += " AND title LIKE ?"
            params.append(f"%{q}%")
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(MAX_LIMIT if needs_post_filter else clamp_limit(limit))

        rows = enrich_rows(run_sql(sql, params=tuple(params)), load_rules())
        if category is not None:
            rows = [row for row in rows if row["category"] == category]
        if session is not None:
            rows = [row for row in rows if row["session_id"] == session]
        # ponytail: category/session post-filter over a bounded 2000-row window;
        # add a materialized column if this ever under-returns.
        return rows[: clamp_limit(limit)]
