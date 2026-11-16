"""SIS posting port, owned by `disbursement`. Adapter: app.adapters.sis_http.HttpSisAdapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.kernel import IdempotencyKey, Money, StudentId, TermId


@dataclass(frozen=True)
class SisPostingReceipt:
    sis_transaction_id: str
    posted_at: datetime


class SisPostingPort(Protocol):
    def post_disbursement_credit(
        self,
        *,
        student_id: StudentId,
        term_id: TermId,
        amount: Money,
        idempotency_key: IdempotencyKey,
    ) -> SisPostingReceipt:
        """Credit the student's tuition balance. Raises kernel.SisUnavailable. Same key -> same receipt."""
        ...
