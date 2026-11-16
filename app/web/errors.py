"""Error mapping for HTTP.

`not_implemented_handler` is skeleton plumbing: any NotImplementedError raised while serving a route
becomes HTTP 501 {"error": "not_implemented", "message": ...}, naming the route's mapped function.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.kernel import DomainError


async def not_implemented_handler(request: Request, exc: Exception) -> JSONResponse:
    route = request.scope.get("route")
    function_name = getattr(route, "name", None) or "unknown"
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "message": f"{request.method} {request.url.path} maps to {function_name}, which is not implemented yet.",
        },
    )


def to_http_error(exc: DomainError) -> tuple[int, dict[str, str]]:
    """Map a DomainError to (HTTP status, {"error": exc.code, "message": user-facing text}).

    E.g. TryAgainLater -> 503 "try again later" (FR-001.4, FR-003.6); AmountOutOfRange -> 422 with the
    "exceeds your tuition gap of $600" text (AC-01); Forbidden -> 403; *NotFound -> 404.
    """
    raise NotImplementedError("web.to_http_error")
