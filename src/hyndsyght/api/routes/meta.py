"""GET/POST/DELETE /api/rules, GET /api/status, /api/categorize, /api/sessions."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hyndsyght import status
from hyndsyght.api.routes.rows import (
    MAX_LIMIT,
    clamp_limit,
    enrich_rows,
    rollup_sessions,
)
from hyndsyght.categorize.exclude import is_away, should_redact
from hyndsyght.categorize.match import categorize
from hyndsyght.categorize.rules import (
    InvalidPatternError,
    Rules,
    UnknownCategoryError,
    add_pattern,
    load_rules,
    remove_pattern,
)
from hyndsyght.store.query import run_sql


class RulePatternBody(BaseModel):
    category: str
    pattern: str


def _rules_summary(rules: Rules) -> dict[str, Any]:
    return {
        "categories": [
            {"name": name, "patterns": [p.pattern for p in patterns]}
            for name, patterns in rules.categories
        ],
        "redact_patterns": [p.pattern for p in rules.redact_patterns],
        "away_patterns": [p.pattern for p in rules.away_patterns],
    }


def register_meta_routes(router: APIRouter) -> None:
    @router.get("/api/status")
    def status_report() -> dict[str, Any]:
        return status.report()

    @router.get("/api/rules")
    def rules_summary() -> dict[str, Any]:
        return _rules_summary(load_rules())

    @router.post("/api/rules")
    def rules_add_pattern(body: RulePatternBody) -> dict[str, Any]:
        try:
            rules = add_pattern(body.category, body.pattern)
        except InvalidPatternError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _rules_summary(rules)

    @router.delete("/api/rules")
    def rules_remove_pattern(body: RulePatternBody) -> dict[str, Any]:
        try:
            rules = remove_pattern(body.category, body.pattern)
        except UnknownCategoryError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _rules_summary(rules)

    @router.get("/api/categorize")
    def categorize_preview(title: str, kind: str = "window") -> dict[str, Any]:
        rules = load_rules()
        if is_away(title, rules):
            return {"away": True, "redacted": False, "category": None}
        if should_redact(title, rules):
            return {"away": False, "redacted": True, "category": None}
        return {
            "away": False,
            "redacted": False,
            "category": categorize(title, kind, rules),
        }

    @router.get("/api/sessions")
    def list_sessions(
        since: float | None = None, until: float | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM raw_events WHERE source = 'agent'"
        params: list[Any] = []
        if since is not None:
            sql += " AND ts_start >= ?"
            params.append(since)
        if until is not None:
            sql += " AND ts_start <= ?"
            params.append(until)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(MAX_LIMIT)

        rows = enrich_rows(run_sql(sql, params=tuple(params)), load_rules())
        return rollup_sessions(rows)[: clamp_limit(limit)]
