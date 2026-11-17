"""FastAPI entry point: `uvicorn app.main:app`.

Jobs are not started yet: jobs.build_scheduler is a stub. Once implemented, start the scheduler in
`lifespan` and shut it down after `yield`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import ledger
from app.container import Container, build_container
from app.kernel import SYSTEM_ACTOR, DomainError, IdempotencyKey, Money
from app.web import api_router
from app.web.errors import domain_error_handler, not_implemented_handler


DEFAULT_FUND_CAPITAL = "10000.00"


def _seed_default_fund(container: Container) -> None:
    """Demo only (plan.md DQ-5): seed fund-main when SEED_DEFAULT_FUND=1. Tests never set it.
    The fixed idempotency key makes a restart against an existing database a no-op replay (NFR-001.2)."""
    with container.uow_factory(immediate=True) as uow:
        ledger.seed_fund(
            uow,
            fund_id=ledger.DEFAULT_FUND_ID,
            initial_capital=Money.of(DEFAULT_FUND_CAPITAL),
            idempotency_key=IdempotencyKey(f"seed-{ledger.DEFAULT_FUND_ID}"),
            actor=SYSTEM_ACTOR,
            clock=container.clock,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build_container()
    app.state.container = container
    if os.environ.get("SEED_DEFAULT_FUND") == "1":
        _seed_default_fund(container)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Tuition Gap Micro-Loan Service", version="0.1.0-skeleton", lifespan=lifespan)
    app.add_exception_handler(NotImplementedError, not_implemented_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(api_router)
    return app


app = create_app()
