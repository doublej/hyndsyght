"""GET /api/day (one day in full), /api/stats (a light summary per day) and
/api/app-icon (the icon of a tracked app)."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

from hyndsyght import platform
from hyndsyght.categorize.rules import load_rules
from hyndsyght.insights.activity import (
    app_totals,
    day_summary,
    load_spans,
    recorded_bundle,
)
from hyndsyght.insights.intervals import day_bounds

MAX_STATS_DAYS = 366
ICON_PIXELS = 64  # drawn at 16-20 CSS px, so sharp up to 3x screens


def register_activity_routes(router: APIRouter) -> None:
    @router.get("/api/day")
    def day(day: str | None = None) -> dict[str, Any]:
        target = day or datetime.now().astimezone().date().isoformat()
        summary = day_summary(target, load_rules())
        return {**summary, "apps": app_totals(summary["runs"])}

    @router.get("/api/stats")
    def stats(
        days: int = Query(30, ge=1, le=MAX_STATS_DAYS),
    ) -> list[dict[str, Any]]:
        today = datetime.now().astimezone().date()
        rules = load_rules()
        dates = [
            (today - timedelta(days=n)).isoformat() for n in range(days - 1, -1, -1)
        ]
        spans = load_spans(day_bounds(dates[0])[0], day_bounds(dates[-1])[1])
        summaries = []
        for date in dates:
            summary = day_summary(date, rules, spans)
            del summary["runs"], summary["agents"]
            summaries.append(summary)
        return summaries

    @router.get("/api/app-icon")
    def app_icon(app: str) -> Response:
        png = platform.app_icon(app, recorded_bundle(app), ICON_PIXELS)
        if png is None:
            raise HTTPException(status_code=404, detail=f"No icon found for {app}")
        return Response(
            png,
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=86400"},
        )
