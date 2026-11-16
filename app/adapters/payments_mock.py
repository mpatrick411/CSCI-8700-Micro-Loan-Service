"""In-process mock payment processor. Implements repayment.PaymentsPort. Deals in token IDs only (NFR-002.4)."""

from __future__ import annotations

from dataclasses import dataclass

from app.kernel import IdempotencyKey, LoanId, Money
from app.repayment import ChargeResult, PaymentMethodToken, RepaymentSchedule


@dataclass
class MockPaymentsAdapter:
    def charge(
        self,
        *,
        method_token: PaymentMethodToken,
        amount: Money,
        idempotency_key: IdempotencyKey,
    ) -> ChargeResult:
        raise NotImplementedError("adapters.MockPaymentsAdapter.charge")

    def enroll_autopay(
        self,
        *,
        method_token: PaymentMethodToken,
        loan_id: LoanId,
        schedule: RepaymentSchedule,
    ) -> str:
        raise NotImplementedError("adapters.MockPaymentsAdapter.enroll_autopay")
