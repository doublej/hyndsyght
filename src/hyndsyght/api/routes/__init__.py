"""Composes the /api router from feature-scoped sub-modules."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request

from hyndsyght.api.routes.activity import register_activity_routes
from hyndsyght.api.routes.events import register_events_routes
from hyndsyght.api.routes.insights import register_insights_routes
from hyndsyght.api.routes.meta import register_meta_routes
from hyndsyght.importers.api import register_import_routes


def build_router(verify_token: Callable[[Request], None]) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_token)])
    register_activity_routes(router)
    register_events_routes(router)
    register_insights_routes(router)
    register_meta_routes(router)
    register_import_routes(router)
    return router
