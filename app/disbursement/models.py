from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.kernel import DisbursementId, LoanId, Money, StudentId, TermId


class DisbursementStatus(StrEnum):
    PENDING = "pending"
    POSTED = "posted"


@dataclass(frozen=True)
class Disbursement:
    disbursement_id: DisbursementId  # also the SIS idempotency key
    loan_id: LoanId
    student_id: StudentId
    term_id: TermId
    amount: Money
    status: DisbursementStatus
    created_at: datetime
    posted_at: datetime | None
    sis_transaction_id: str | None
    attempts: int
    last_error: str | None


@dataclass(frozen=True)
class PostingRunResult:
    posted: tuple[DisbursementId, ...]
    still_pending: tuple[DisbursementId, ...]
