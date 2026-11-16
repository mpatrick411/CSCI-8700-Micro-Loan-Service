"""FastAPI dependencies for identity. Student-facing services take student_id from here, never from request params."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request

from app.identity.models import CurrentUser, Role
from app.kernel import StudentId

DEV_USER_HEADER = "X-Dev-User"


def get_current_user(request: Request) -> CurrentUser:
    """Resolve the user from the X-Dev-User header via the configured IdentityProvider."""
    raise NotImplementedError("identity.get_current_user")


def require_role(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a dependency that returns the current user if their role is in `roles`.

    The factory itself only builds the dependency (it runs at import time when routes are declared);
    the returned dependency holds the check.
    """

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        raise NotImplementedError("identity.require_role")

    return dependency


def student_id_of(user: CurrentUser) -> StudentId:
    """The StudentId of a Student user. Raises Forbidden for any other role."""
    raise NotImplementedError("identity.student_id_of")
