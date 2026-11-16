from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import NewType

from app.kernel import ApplicationId, FundId, IdempotencyKey, LoanId, Money, PaymentId, StudentId, TermId

# Opaque token issued by the payment processor. The system never sees card or bank numbers (NFR-002.4).
PaymentMethodToken = NewType("PaymentMethodToken", str)


class LoanStatus(StrEnum):
    ACTIVE = "active"
    REPAID = "repaid"


class InstallmentStatus(StrEnum):
    UNSCHEDULED = "unscheduled"  # schedule exists, disbursement not yet posted
    DUE = "due"
    PAID = "paid"
    OVERDUE = "overdue"


class PaymentKind(StrEnum):
    ONE_TIME = "one_time"
    AUTOPAY = "autopay"


@dataclass(frozen=True)
class Installment:
    loan_id: LoanId
    number: int  # 1-based
    amount: Money
    due_date: date | None
    amount_paid: Money
    status: InstallmentStatus
    reminder_sent_at: datetime | None
    overdue_since: date | None


@dataclass(frozen=True)
class RepaymentSchedule:
    loan_id: LoanId
    interest_rate: Decimal  # always 0 (FR-005.1)
    installments: tuple[Installment, ...]


@dataclass(frozen=True)
class Loan:
    loan_id: LoanId
    application_id: ApplicationId
    student_id: StudentId
    term_id: TermId
    fund_id: FundId
    principal: Money
    outstanding: Money
    status: LoanStatus
    flagged_for_follow_up: bool  # FR-006.3
    created_at: datetime


@dataclass(frozen=True)
class Payment:
    payment_id: PaymentId
    loan_id: LoanId
    student_id: StudentId
    amount: Money
    kind: PaymentKind
    method_token: PaymentMethodToken
    processor_charge_id: str
    idempotency_key: IdempotencyKey
    paid_at: datetime


@dataclass(frozen=True)
class AutopayEnrollment:
    loan_id: LoanId
    student_id: StudentId
    method_token: PaymentMethodToken
    processor_mandate_id: str
    enrolled_at: datetime
