"""Composition root: chooses one adapter per port at startup (architecture.md, "Ports and prototype adapters")."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.adapters.esign_mock import ClickToSignAdapter
from app.adapters.identity_seeded import SeededIdentityProvider
from app.adapters.notifications_outbox import OutboxNotifier
from app.adapters.payments_mock import MockPaymentsAdapter
from app.adapters.sis_http import HttpSisAdapter
from app.kernel import AdjustableClock, SqliteUnitOfWorkFactory


@dataclass
class Container:
    clock: AdjustableClock
    uow_factory: SqliteUnitOfWorkFactory
    sis: HttpSisAdapter
    payments: MockPaymentsAdapter
    esign: ClickToSignAdapter
    notifier: OutboxNotifier
    identity: SeededIdentityProvider


def build_container() -> Container:
    """Wire the prototype adapters. Construction only: no I/O, no database connection."""
    return Container(
        clock=AdjustableClock(),
        uow_factory=SqliteUnitOfWorkFactory(os.environ.get("DATABASE_URL", "sqlite:///./data/loans.db")),
        sis=HttpSisAdapter(base_url=os.environ.get("SIS_BASE_URL", "http://localhost:8001")),
        payments=MockPaymentsAdapter(),
        esign=ClickToSignAdapter(),
        notifier=OutboxNotifier(),
        identity=SeededIdentityProvider(),
    )
