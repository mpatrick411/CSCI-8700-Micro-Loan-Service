"""Ports owned by `repayment`.

Payments adapter: app.adapters.payments_mock.MockPaymentsAdapter.
Notifications adapter: app.adapters.notifications_outbox.OutboxNotifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.kernel import IdempotencyKey, LoanId, Money, StudentId, UnitOfWork
from app.repayment.models import PaymentMethodToken, RepaymentSchedule


@dataclass(frozen=True)
class ChargeResult:
    succeeded: bool
    processor_charge_id: str | None
    failure_reason: str | None


class PaymentsPort(Protocol):
    def charge(
        self,
        *,
        method_token: PaymentMethodToken,
        amount: Money,
        idempotency_key: IdempotencyKey,
    ) -> ChargeResult: ...

    def enroll_autopay(
        self,
        *,
        method_token: PaymentMethodToken,
        loan_id: LoanId,
        schedule: RepaymentSchedule,
    ) -> str:
        """Returns the processor's mandate id."""
        ...


class NotificationsPort(Protocol):
    def send(
        self,
        uow: UnitOfWork,
        *,
        student_id: StudentId,
        subject: str,
        body: str,
        idempotency_key: IdempotencyKey,
    ) -> str:
        """Queue a message in the same transaction as the state change. Returns the message id."""
        ...
