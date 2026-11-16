"""web: HTTP routes and mapping of domain errors to user messages. Depends on identity and domain services."""

from app.web.router import api_router

__all__ = ["api_router"]
