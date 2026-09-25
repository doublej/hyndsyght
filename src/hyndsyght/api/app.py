"""FastAPI app: Host-header guard, token auth, bounded API, and the built dashboard.

Static dir resolves relative to the installed package, so it works
identically in dev (after `just web-build`, which also symlinks it into
place) and once wheel-installed (where hatch's force-include put it there
for real).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from hyndsyght.api.auth import HostGuardMiddleware, ensure_token, token_dependency
from hyndsyght.api.routes import build_router

STATIC_DIR = Path(__file__).parent.parent / "static"
TOKEN_PLACEHOLDER = "__HYNDSYGHT_TOKEN_PLACEHOLDER__"


def create_app(port: int) -> FastAPI:
    token = ensure_token()
    app = FastAPI(title="hyndsyght")
    app.add_middleware(
        HostGuardMiddleware, allowed_hosts={f"127.0.0.1:{port}", f"localhost:{port}"}
    )
    app.include_router(build_router(token_dependency(token)))

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        html = (STATIC_DIR / "index.html").read_text()
        return html.replace(TOKEN_PLACEHOLDER, token)

    if (STATIC_DIR / "assets").exists():
        app.mount(
            "/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets"
        )

    return app
