"""web: HTTP routes and mapping of domain errors to user messages. Depends on identity and domain services."""

from app.web.deps import to_jsonable
from app.web.errors import domain_error_handler, to_http_error
from app.web.router import api_router

__all__ = ["api_router", "domain_error_handler", "to_http_error", "to_jsonable"]
