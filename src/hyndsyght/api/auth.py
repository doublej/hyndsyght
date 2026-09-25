"""Token + Host-header auth.

No CORS middleware anywhere in this app — its absence is the security
feature: same-origin policy then blocks cross-origin reads outright.
"""

import hmac
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse, Response

from hyndsyght import paths


def ensure_token(token_path: Path | None = None) -> str:
    path = token_path or paths.token_path()
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32))
        path.chmod(0o600)
    return path.read_text().strip()


class HostGuardMiddleware(BaseHTTPMiddleware):
    """Rejects any request whose Host header isn't an allowed loopback host:port.

    Defeats DNS rebinding — the browser still sends the real Host post-rebind.
    """

    def __init__(self, app: object, allowed_hosts: set[str]) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.allowed_hosts = allowed_hosts

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Can't raise HTTPException here — ExceptionMiddleware sits inside user
        # middleware in Starlette's stack, not around it, so it wouldn't be caught.
        if request.headers.get("host", "") not in self.allowed_hosts:
            return PlainTextResponse("Host header not allowed", status_code=403)
        return await call_next(request)


def token_dependency(token: str) -> Callable[[Request], None]:
    def verify(request: Request) -> None:
        provided = (
            request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        )
        if not hmac.compare_digest(provided, token):
            raise HTTPException(status_code=401, detail="Invalid token")

    return verify
