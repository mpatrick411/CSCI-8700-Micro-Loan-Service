from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.kernel import AgreementId, ApplicationId, FundId, LoanId, Money, StudentId, TermId


class AgreementStatus(StrEnum):
    PENDING_SIGNATURE = "pending_signature"
    SIGNED = "signed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ConsentInput:
    """What the student affirms when signing (NFR-004.1)."""

    consent_to_electronic_records: bool
    intent_to_sign: bool
    typed_name: str


@dataclass(frozen=True)
class ConsentRecord:
    consent_to_electronic_records: bool
    intent_to_sign: bool
    typed_name: str
    consented_at: datetime


@dataclass(frozen=True)
class RenderedDocument:
    filename: str
    content_type: str  # "application/pdf"
    content: bytes
    sha256: str


@dataclass(frozen=True)
class LoanAgreement:
    agreement_id: AgreementId
    application_id: ApplicationId
    student_id: StudentId
    term_id: TermId
    fund_id: FundId
    amount: Money
    interest_rate: Decimal  # 0 (FR-005.1)
    installment_amounts: tuple[Money, ...]
    template_version: str  # counsel-approved text plugs in here (NFR-004.4)
    status: AgreementStatus
    created_at: datetime
    sign_by: datetime  # created_at + signing_window_days (FR-004.3)
    signed_at: datetime | None
    document_sha256: str | None  # of the stored signed PDF (NFR-004.2)
    consent: ConsentRecord | None
    loan_id: LoanId | None
