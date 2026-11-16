"""Unit-of-work transaction boundary over SQLAlchemy + SQLite.

`immediate=True` opens the transaction with `BEGIN IMMEDIATE` so a balance check and a reservation
cannot interleave with another writer (NFR-001.1). On Postgres this becomes SELECT ... FOR UPDATE.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Protocol

from sqlalchemy.orm import Session


class UnitOfWork(Protocol):
    @property
    def session(self) -> Session: ...

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self, *, immediate: bool = False) -> UnitOfWork: ...


@dataclass
class SqlAlchemyUnitOfWork:
    """One transaction. Commits on clean exit, rolls back on exception."""

    database_url: str
    immediate: bool = False

    @property
    def session(self) -> Session:
        raise NotImplementedError("kernel.SqlAlchemyUnitOfWork.session")

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        raise NotImplementedError("kernel.SqlAlchemyUnitOfWork.__enter__")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError("kernel.SqlAlchemyUnitOfWork.__exit__")

    def commit(self) -> None:
        raise NotImplementedError("kernel.SqlAlchemyUnitOfWork.commit")

    def rollback(self) -> None:
        raise NotImplementedError("kernel.SqlAlchemyUnitOfWork.rollback")


@dataclass
class SqliteUnitOfWorkFactory:
    """Creates SqlAlchemyUnitOfWork instances for one SQLite file. Construction does no I/O."""

    database_url: str

    def __call__(self, *, immediate: bool = False) -> SqlAlchemyUnitOfWork:
        raise NotImplementedError("kernel.SqliteUnitOfWorkFactory.__call__")
