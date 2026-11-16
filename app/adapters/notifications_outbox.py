"""Outbox-table notifier. Implements repayment.NotificationsPort; list_for backs the mock inbox (FR-005.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.kernel import IdempotencyKey, StudentId, UnitOfWork


@dataclass(frozen=True)
class OutboxMessage:
    message_id: str
    student_id: StudentId
    subject: str
    body: str
    created_at: datetime


@dataclass
class OutboxNotifier:
    def send(
        self,
        uow: UnitOfWork,
        *,
        student_id: StudentId,
        subject: str,
        body: str,
        idempotency_key: IdempotencyKey,
    ) -> str:
        raise NotImplementedError("adapters.OutboxNotifier.send")

    def list_for(self, uow: UnitOfWork, *, student_id: StudentId) -> list[OutboxMessage]:
        raise NotImplementedError("adapters.OutboxNotifier.list_for")
