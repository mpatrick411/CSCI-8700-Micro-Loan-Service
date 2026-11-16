"""FastAPI entry point: `uvicorn app.main:app`.

Jobs are not started yet: jobs.build_scheduler is a stub. Once implemented, start the scheduler in
`lifespan` and shut it down after `yield`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import build_container
from app.web import api_router
from app.web.errors import not_implemented_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.container = build_container()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Tuition Gap Micro-Loan Service", version="0.1.0-skeleton", lifespan=lifespan)
    app.add_exception_handler(NotImplementedError, not_implemented_handler)
    app.include_router(api_router)
    return app


app = create_app()
