"""Unit-of-work transaction boundary over SQLAlchemy + SQLite.

`immediate=True` opens the transaction with `BEGIN IMMEDIATE` so a balance check and a reservation
cannot interleave with another writer (NFR-001.1). On Postgres this becomes SELECT ... FOR UPDATE.

Schema (DQ-1): every module may keep its own SQLAlchemy tables in `app/<module>/tables.py`, declared on the
shared `metadata` below. On its first call, `SqliteUnitOfWorkFactory` imports every such `tables.py` and
creates whatever does not exist yet (tables, plus the DDL a module attaches to them, such as the audit
triggers). Constructing the factory does no I/O.
"""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

# Shared by every module's tables.py. Each module declares only its own tables on it.
metadata = MetaData()

_APP_PACKAGE = __name__.rsplit(".", 2)[0]  # "app"
_TABLES_MODULE = "tables"
_BEGIN_OPTION = "sqlite_begin"

_engines: dict[str, Engine] = {}
_engines_lock = threading.Lock()


def _engine_for(database_url: str) -> Engine:
    """One Engine per database URL. SQLite connections are opened per unit of work (NullPool)."""
    with _engines_lock:
        engine = _engines.get(database_url)
        if engine is None:
            engine = create_engine(database_url, poolclass=NullPool, connect_args={"check_same_thread": False})
            _take_over_transaction_control(engine)
            _engines[database_url] = engine
        return engine


def _take_over_transaction_control(engine: Engine) -> None:
    """Make SQLAlchemy, not pysqlite, emit BEGIN, so a unit of work can choose BEGIN IMMEDIATE."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        dbapi_connection.isolation_level = None  # driver autocommit; transactions start with our BEGIN

    @event.listens_for(engine, "begin")
    def _on_begin(connection: Any) -> None:
        mode = connection.get_execution_options().get(_BEGIN_OPTION, "DEFERRED")
        connection.exec_driver_sql(f"BEGIN {mode}")


def _import_all_tables_modules() -> None:
    """Import `app.<module>.tables` for every module that has one, so its tables are on `metadata`."""
    package = importlib.import_module(_APP_PACKAGE)
    for module in pkgutil.iter_modules(package.__path__):
        if not module.ispkg:
            continue
        name = f"{_APP_PACKAGE}.{module.name}.{_TABLES_MODULE}"
        if importlib.util.find_spec(name) is not None:
            importlib.import_module(name)


def _ensure_sqlite_directory(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


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
    _session: Session | None = field(default=None, init=False, repr=False)

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("the unit of work is not active; use it as a context manager")
        return self._session

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        if self._session is not None:
            raise RuntimeError("the unit of work is already active")
        mode = "IMMEDIATE" if self.immediate else "DEFERRED"
        bind = _engine_for(self.database_url).execution_options(**{_BEGIN_OPTION: mode})
        self._session = Session(bind=bind, expire_on_commit=False)
        # Begin now, so BEGIN IMMEDIATE takes the write lock before any read of this transaction.
        self._session.connection()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.session.close()
            self._session = None

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@dataclass
class SqliteUnitOfWorkFactory:
    """Creates SqlAlchemyUnitOfWork instances for one SQLite file. Construction does no I/O."""

    database_url: str
    _schema_ready: bool = field(default=False, init=False, repr=False)
    _schema_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __call__(self, *, immediate: bool = False) -> SqlAlchemyUnitOfWork:
        self._ensure_schema()
        return SqlAlchemyUnitOfWork(self.database_url, immediate=immediate)

    def _ensure_schema(self) -> None:
        """First call only: create every module's tables (and their attached DDL) that do not exist yet."""
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return
            _import_all_tables_modules()
            _ensure_sqlite_directory(self.database_url)
            metadata.create_all(_engine_for(self.database_url), checkfirst=True)
            self._schema_ready = True
