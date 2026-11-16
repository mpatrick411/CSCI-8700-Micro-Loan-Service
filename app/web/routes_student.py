"""Student-facing routes. student_id always comes from the resolved user (NFR-002.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Response

from app import agreements, applications, disbursement, repayment
from app.agreements import ConsentInput
from app.kernel import Actor, AgreementId, ApplicationId, IdempotencyKey, LoanId, Money, TermId
from app.identity import student_id_of
from app.repayment import PaymentMethodToken
from app.web.deps import ContainerDep, StudentUser
from app.web.schemas import (
    AppealRequest,
    AutopayRequest,
    PaymentRequest,
    SignAgreementRequest,
    SubmitApplicationRequest,
    ValidateAmountRequest,
)

router = APIRouter(tags=["student"])
IdempotencyHeader = Annotated[str, Header(alias="Idempotency-Key")]


# --- Applications (FR-001, FR-002) ---------------------------------------------------------------


@router.get("/terms/{term_id}/application-start", name="applications.start")
def start_application(term_id: str, user: StudentUser, c: ContainerDep):
    return applications.start(
        uow_factory=c.uow_factory, sis=c.sis, student_id=student_id_of(user), term_id=TermId(term_id)
    )


@router.post("/applications/validate-amount", name="applications.validate_amount")
def validate_amount(body: ValidateAmountRequest, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return applications.validate_amount(
            uow, requested_amount=Money.of(body.requested_amount), tuition_gap=Money.of(body.tuition_gap)
        )


@router.post("/applications", name="applications.submit", status_code=201)
def submit_application(
    body: SubmitApplicationRequest, idempotency_key: IdempotencyHeader, user: StudentUser, c: ContainerDep
):
    return applications.submit(
        uow_factory=c.uow_factory,
        sis=c.sis,
        clock=c.clock,
        student_id=student_id_of(user),
        term_id=TermId(body.term_id),
        requested_amount=Money.of(body.requested_amount),
        idempotency_key=IdempotencyKey(idempotency_key),
    )


@router.get("/applications", name="applications.list_for_student")
def list_applications(user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return applications.list_for_student(uow, student_id=student_id_of(user))


@router.get("/applications/{application_id}", name="applications.get")
def get_application(application_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return applications.get(
            uow, application_id=ApplicationId(application_id), student_id=student_id_of(user)
        )


@router.post("/applications/{application_id}/appeal", name="applications.appeal", status_code=201)
def appeal_application(application_id: str, body: AppealRequest, user: StudentUser, c: ContainerDep):
    with c.uow_factory(immediate=True) as uow:
        return applications.appeal(
            uow,
            application_id=ApplicationId(application_id),
            student_id=student_id_of(user),
            explanation=body.explanation,
            clock=c.clock,
        )


# --- Agreements (FR-004, NFR-004) ----------------------------------------------------------------


@router.get("/agreements/{agreement_id}", name="agreements.get")
def get_agreement(agreement_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return agreements.get(uow, agreement_id=AgreementId(agreement_id), student_id=student_id_of(user))


@router.get("/agreements/{agreement_id}/document", name="agreements.render_for_review")
def review_agreement_document(agreement_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        doc = agreements.render_for_review(
            uow, agreement_id=AgreementId(agreement_id), student_id=student_id_of(user), esign=c.esign
        )
    return Response(content=doc.content, media_type=doc.content_type)


@router.post("/agreements/{agreement_id}/signature", name="agreements.sign")
def sign_agreement(agreement_id: str, body: SignAgreementRequest, user: StudentUser, c: ContainerDep):
    with c.uow_factory(immediate=True) as uow:
        return agreements.sign(
            uow,
            agreement_id=AgreementId(agreement_id),
            student_id=student_id_of(user),
            consent=ConsentInput(
                consent_to_electronic_records=body.consent_to_electronic_records,
                intent_to_sign=body.intent_to_sign,
                typed_name=body.typed_name,
            ),
            esign=c.esign,
            clock=c.clock,
        )


@router.get("/agreements/{agreement_id}/signed-document", name="agreements.download_signed")
def download_signed_agreement(agreement_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        doc = agreements.download_signed(
            uow, agreement_id=AgreementId(agreement_id), student_id=student_id_of(user)
        )
    return Response(
        content=doc.content,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


# --- Loans and repayment (FR-005, FR-006.2) ------------------------------------------------------


@router.get("/loans", name="repayment.list_loans")
def list_loans(user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return repayment.list_loans(uow, student_id=student_id_of(user))


@router.get("/loans/{loan_id}", name="repayment.get_loan")
def get_loan(loan_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return repayment.get_loan(uow, loan_id=LoanId(loan_id), student_id=student_id_of(user))


@router.get("/loans/{loan_id}/schedule", name="repayment.get_schedule")
def get_schedule(loan_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return repayment.get_schedule(uow, loan_id=LoanId(loan_id), student_id=student_id_of(user))


@router.get("/loans/{loan_id}/disbursement", name="disbursement.get_for_loan")
def get_disbursement(loan_id: str, user: StudentUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return disbursement.get_for_loan(uow, loan_id=LoanId(loan_id), student_id=student_id_of(user))


@router.post("/loans/{loan_id}/payments", name="repayment.make_payment", status_code=201)
def make_payment(
    loan_id: str, body: PaymentRequest, idempotency_key: IdempotencyHeader, user: StudentUser, c: ContainerDep
):
    with c.uow_factory(immediate=True) as uow:
        return repayment.make_payment(
            uow,
            loan_id=LoanId(loan_id),
            student_id=student_id_of(user),
            amount=Money.of(body.amount),
            method_token=PaymentMethodToken(body.method_token),
            idempotency_key=IdempotencyKey(idempotency_key),
            payments=c.payments,
            actor=Actor(user.user_id),
            clock=c.clock,
        )


@router.post("/loans/{loan_id}/autopay", name="repayment.enroll_autopay", status_code=201)
def enroll_autopay(loan_id: str, body: AutopayRequest, user: StudentUser, c: ContainerDep):
    with c.uow_factory(immediate=True) as uow:
        return repayment.enroll_autopay(
            uow,
            loan_id=LoanId(loan_id),
            student_id=student_id_of(user),
            method_token=PaymentMethodToken(body.method_token),
            payments=c.payments,
            actor=Actor(user.user_id),
            clock=c.clock,
        )


@router.get("/notifications", name="adapters.OutboxNotifier.list_for")
def list_notifications(user: StudentUser, c: ContainerDep):
    """Mock inbox showing reminders from the outbox (FR-005.3)."""
    with c.uow_factory() as uow:
        return c.notifier.list_for(uow, student_id=student_id_of(user))
