"""FastAPI dependencies for identity. Student-facing services take student_id from here, never from request params."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request

from app.identity.errors import Forbidden, Unauthenticated
from app.identity.models import CurrentUser, Role
from app.identity.ports import IdentityProvider
from app.kernel import StudentId

DEV_USER_HEADER = "X-Dev-User"


def get_current_user(request: Request) -> CurrentUser:
    """Resolve the user from the X-Dev-User header via the configured IdentityProvider."""
    user_ref = (request.headers.get(DEV_USER_HEADER) or "").strip()
    if not user_ref:
        raise Unauthenticated(f"Sign in to continue (missing {DEV_USER_HEADER} header).")
    provider: IdentityProvider = request.app.state.container.identity
    user = provider.resolve(user_ref)
    if user is None:
        raise Unauthenticated("Sign in to continue (unknown user).")
    return user


def require_role(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a dependency that returns the current user if their role is in `roles`.

    The factory itself only builds the dependency (it runs at import time when routes are declared);
    the returned dependency holds the check.
    """

    allowed = frozenset(roles)

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise Forbidden("You do not have access to this page.")
        return user

    return dependency


def student_id_of(user: CurrentUser) -> StudentId:
    """The StudentId of a Student user. Raises Forbidden for any other role."""
    if user.role != Role.STUDENT or user.student_id is None:
        raise Forbidden("Only students have a student record.")
    return user.student_id
