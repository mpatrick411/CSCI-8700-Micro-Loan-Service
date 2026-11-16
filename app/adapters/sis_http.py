"""HTTP client to the mock SIS container. Implements applications.SisReaderPort and disbursement.SisPostingPort.

Turns timeout, transport error, incomplete payloads and unrecognised values (e.g. an unknown SAP status)
into kernel.SisUnavailable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.applications import StudentTermData
from app.disbursement import SisPostingReceipt
from app.kernel import IdempotencyKey, Money, StudentId, TermId


@dataclass
class HttpSisAdapter:
    base_url: str
    timeout_seconds: float = 3.0  # NFR-005.2

    def get_student_term_data(self, *, student_id: StudentId, term_id: TermId) -> StudentTermData:
        raise NotImplementedError("adapters.HttpSisAdapter.get_student_term_data")

    def post_disbursement_credit(
        self,
        *,
        student_id: StudentId,
        term_id: TermId,
        amount: Money,
        idempotency_key: IdempotencyKey,
    ) -> SisPostingReceipt:
        raise NotImplementedError("adapters.HttpSisAdapter.post_disbursement_credit")
