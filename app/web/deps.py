"""Request-scoped plumbing shared by routes."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, cast

from fastapi import Depends, Request

from app.container import Container
from app.identity import CurrentUser, Role, get_current_user, require_role
from app.kernel import Money

_CENT = Decimal("0.01")


def to_jsonable(value: Any) -> Any:
    """JSON-ready data for a route's result (contracts.md "Money" convention, NFR-001.3).

    Money -> 2-place decimal string ("600.00"); datetime -> ISO 8601 with its UTC offset; date -> ISO date;
    enums -> their value; dataclasses, tuples, lists and mappings recursively. FastAPI's own encoder would
    turn Money into {"amount": 600.0}, so routes return JSONResponse(to_jsonable(result), status_code=...).
    """
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Money):
        return str(value.amount.quantize(_CENT))
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"datetime {value!r} has no UTC offset")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(to_jsonable(k)): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    raise TypeError(f"cannot convert {type(value).__name__} to JSON")


def get_container(request: Request) -> Container:
    """The adapters chosen at startup (stored on app.state by create_app)."""
    return cast(Container, request.app.state.container)


ContainerDep = Annotated[Container, Depends(get_container)]
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
StudentUser = Annotated[CurrentUser, Depends(require_role(Role.STUDENT))]
OfficerUser = Annotated[CurrentUser, Depends(require_role(Role.OFFICER))]
AdminUser = Annotated[CurrentUser, Depends(require_role(Role.ADMIN))]
OfficerOrAdmin = Annotated[CurrentUser, Depends(require_role(Role.OFFICER, Role.ADMIN))]
