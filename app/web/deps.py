"""Request-scoped plumbing shared by routes."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from app.container import Container
from app.identity import CurrentUser, Role, get_current_user, require_role


def get_container(request: Request) -> Container:
    """The adapters chosen at startup (stored on app.state by create_app)."""
    return cast(Container, request.app.state.container)


ContainerDep = Annotated[Container, Depends(get_container)]
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
StudentUser = Annotated[CurrentUser, Depends(require_role(Role.STUDENT))]
OfficerUser = Annotated[CurrentUser, Depends(require_role(Role.OFFICER))]
AdminUser = Annotated[CurrentUser, Depends(require_role(Role.ADMIN))]
OfficerOrAdmin = Annotated[CurrentUser, Depends(require_role(Role.OFFICER, Role.ADMIN))]
