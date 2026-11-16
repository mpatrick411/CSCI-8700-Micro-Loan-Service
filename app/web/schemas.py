"""Request bodies. Send money as decimal strings ("600.00"); they become kernel.Money (NFR-001.3)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.config import ConfigKey
from app.review import ReviewDecision


class ValidateAmountRequest(BaseModel):
    requested_amount: Decimal
    tuition_gap: Decimal  # as shown by application-start; submit re-reads the SIS anyway


class SubmitApplicationRequest(BaseModel):
    term_id: str
    requested_amount: Decimal


class AppealRequest(BaseModel):
    explanation: str | None = None


class ResolveReviewRequest(BaseModel):
    decision: ReviewDecision
    rationale: str  # emptiness is checked by review.resolve (FR-003.2), not here


class SignAgreementRequest(BaseModel):
    consent_to_electronic_records: bool
    intent_to_sign: bool
    typed_name: str


class PaymentRequest(BaseModel):
    amount: Decimal
    method_token: str  # processor token, never a card or account number (NFR-002.4)


class AutopayRequest(BaseModel):
    method_token: str


class ConfigUpdateRequest(BaseModel):
    changes: dict[ConfigKey, str]


class AdvanceClockRequest(BaseModel):
    days: int = 0
    hours: int = 0
