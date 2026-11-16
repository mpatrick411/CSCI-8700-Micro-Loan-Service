from __future__ import annotations

from app.agreements.models import ConsentInput, LoanAgreement, RenderedDocument
from app.agreements.ports import ESignaturePort
from app.kernel import (
    Actor,
    AgreementId,
    ApplicationId,
    Clock,
    FundId,
    Money,
    StudentId,
    TermId,
    UnitOfWork,
)


def generate(
    uow: UnitOfWork,
    *,
    application_id: ApplicationId,
    student_id: StudentId,
    term_id: TermId,
    fund_id: FundId,
    amount: Money,
    actor: Actor,
    clock: Clock,
) -> LoanAgreement:
    """Create the agreement in PENDING_SIGNATURE with amount and repayment terms (FR-004.1)."""
    raise NotImplementedError("agreements.generate")


def get(uow: UnitOfWork, *, agreement_id: AgreementId, student_id: StudentId) -> LoanAgreement:
    raise NotImplementedError("agreements.get")


def render_for_review(
    uow: UnitOfWork,
    *,
    agreement_id: AgreementId,
    student_id: StudentId,
    esign: ESignaturePort,
) -> RenderedDocument:
    raise NotImplementedError("agreements.render_for_review")


def sign(
    uow: UnitOfWork,
    *,
    agreement_id: AgreementId,
    student_id: StudentId,
    consent: ConsentInput,
    esign: ESignaturePort,
    clock: Clock,
) -> LoanAgreement:
    """In one transaction: check the signing window, capture the signature, compare-and-set to SIGNED,
    ledger.disburse (key = agreement id), repayment.create_loan, disbursement.create_pending, audit.
    Retrying a successful sign returns the signed agreement unchanged (NFR-001.2)."""
    raise NotImplementedError("agreements.sign")


def find_unsigned_past_window(uow: UnitOfWork, *, clock: Clock) -> list[LoanAgreement]:
    raise NotImplementedError("agreements.find_unsigned_past_window")


def expire(uow: UnitOfWork, *, agreement_id: AgreementId, actor: Actor, clock: Clock) -> LoanAgreement:
    """Compare-and-set PENDING_SIGNATURE -> EXPIRED. Called by applications.expire_unsigned."""
    raise NotImplementedError("agreements.expire")


def download_signed(uow: UnitOfWork, *, agreement_id: AgreementId, student_id: StudentId) -> RenderedDocument:
    """The stored signed PDF, byte-for-byte (NFR-004.2, NFR-004.3)."""
    raise NotImplementedError("agreements.download_signed")
