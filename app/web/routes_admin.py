"""Identity, configuration and demo-clock routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter

from app import config
from app.kernel import Actor
from app.web.deps import AdminUser, AnyUser, ContainerDep
from app.web.schemas import AdvanceClockRequest, ConfigUpdateRequest

router = APIRouter()


@router.get("/me", name="identity.get_current_user", tags=["identity"])
def me(user: AnyUser):
    return user


@router.get("/dev/users", name="adapters.SeededIdentityProvider.list_users", tags=["identity"])
def dev_users(c: ContainerDep):
    """Users for the dev user-switcher. Unauthenticated by design (prototype only)."""
    return c.identity.list_users()


@router.get("/config", name="config.current", tags=["admin"])
def get_config(user: AnyUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return config.current(uow)


@router.patch("/config", name="config.update", tags=["admin"])
def update_config(body: ConfigUpdateRequest, user: AdminUser, c: ContainerDep):
    with c.uow_factory(immediate=True) as uow:
        return config.update(uow, changes=body.changes, actor=Actor(user.user_id), clock=c.clock)


@router.post("/admin/clock/advance", name="config.advance_clock", tags=["admin"])
def advance_clock(body: AdvanceClockRequest, user: AdminUser, c: ContainerDep):
    with c.uow_factory(immediate=True) as uow:
        return config.advance_clock(
            uow, clock=c.clock, by=timedelta(days=body.days, hours=body.hours), actor=Actor(user.user_id)
        )
