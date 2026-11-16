"""Public service functions of `applications`.

Functions that call the SIS take a UnitOfWorkFactory so every SIS call happens before the write
transaction opens (architecture.md, "All SIS calls made before the write transaction opens").
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app import config
from app.applications.models import (
    AmountValidation,
    ApplicationStart,
    ApplicationStatus,
    Decision,
    DecisionOutcome,
    DecisionSource,
    LoanApplication,
    StudentTermData,
    SubmissionResult,
)
from app.applications.ports import SisReaderPort
from app.applications.tables import application_decisions, applications
from app.eligibility import (
    EligibilityAssessment,
    EligibilityInput,
    Outcome,
    RuleName,
    RuleResult,
    SapStatus,
)
from app.kernel import (
    Actor,
    AgreementId,
    ApplicationId,
    Clock,
    FundId,
    IdempotencyKey,
    Money,
    ReviewId,
    StudentId,
    TermId,
    UnitOfWork,
    UnitOfWorkFactory,
    UserId,
)
from app.review import ExceptionReview, ReviewDecision

# --- Storage mapping (rows of applications/tables.py -> domain objects) ----------------------------


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _assessment_from_json(text: str) -> EligibilityAssessment:
    data = json.loads(text)
    inputs = data["inputs"]
    return EligibilityAssessment(
        rule_set_version=data["rule_set_version"],
        inputs=EligibilityInput(
            requested_amount=Money.of(inputs["requested_amount"]),
            enrollment_credits=inputs["enrollment_credits"],
            sap_status=SapStatus(inputs["sap_status"]),
            fund_available_balance=Money.of(inputs["fund_available_balance"]),
            has_overdue_installment=inputs["has_overdue_installment"],
        ),
        results=tuple(
            RuleResult(rule=RuleName(r["rule"]), outcome=Outcome(r["outcome"]), reason=r["reason"])
            for r in data["results"]
        ),
    )


def _decision_from_row(row: Any) -> Decision:
    return Decision(
        outcome=DecisionOutcome(row.outcome),
        source=DecisionSource(row.source),
        reasons=tuple(json.loads(row.reasons)),
        decided_by=Actor(row.decided_by),
        decided_at=datetime.fromisoformat(row.decided_at),
        rationale=row.rationale,
        rule_set_version=row.rule_set_version,
    )


def _load_applications(uow: UnitOfWork, *conditions: Any) -> list[LoanApplication]:
    """Applications matching `conditions`, each with its decisions (oldest first)."""
    rows = uow.session.execute(
        select(applications).where(*conditions).order_by(applications.c.submitted_at, applications.c.application_id)
    ).all()
    if not rows:
        return []
    ids = [row.application_id for row in rows]
    decisions: dict[str, list[Decision]] = {application_id: [] for application_id in ids}
    for d in uow.session.execute(
        select(application_decisions)
        .where(application_decisions.c.application_id.in_(ids))
        .order_by(application_decisions.c.application_id, application_decisions.c.seq)
    ).all():
        decisions[d.application_id].append(_decision_from_row(d))
    return [
        LoanApplication(
            application_id=ApplicationId(row.application_id),
            student_id=StudentId(row.student_id),
            term_id=TermId(row.term_id),
            fund_id=FundId(row.fund_id),
            requested_amount=Money.from_cents(row.requested_amount_cents),
            tuition_gap_at_submission=Money.from_cents(row.tuition_gap_cents),
            status=ApplicationStatus(row.status),
            submitted_at=datetime.fromisoformat(row.submitted_at),
            assessment=_assessment_from_json(row.assessment),
            decisions=tuple(decisions[row.application_id]),
            appealed_at=_parse_datetime(row.appealed_at),
            review_id=ReviewId(row.review_id) if row.review_id is not None else None,
            agreement_id=AgreementId(row.agreement_id) if row.agreement_id is not None else None,
        )
        for row in rows
    ]


def _pending_aid_total(data: StudentTermData) -> Money:
    """Sum of AidAwards that are accepted but not yet disbursed (FR-001.1)."""
    total = Money.zero()
    for award in data.aid_awards:
        if award.accepted and not award.disbursed:
            total = total + award.amount
    return total


# --- Public service functions --------------------------------------------------------------------


def calculate_tuition_gap(data: StudentTermData) -> Money:
    """tuition_balance minus accepted-but-undisbursed aid (FR-001.1). Pure; may be zero or negative."""
    return data.tuition_balance - _pending_aid_total(data)


def validate_amount(uow: UnitOfWork, *, requested_amount: Money, tuition_gap: Money) -> AmountValidation:
    """Live HTMX check against the gap and the configured min/max (FR-001.3). Never raises for a bad amount."""
    raise NotImplementedError("applications.validate_amount")


def start(
    *,
    uow_factory: UnitOfWorkFactory,
    sis: SisReaderPort,
    student_id: StudentId,
    term_id: TermId,
) -> ApplicationStart:
    """Read the SIS, calculate the gap and limits. Creates nothing (FR-001.6)."""
    # The SIS call happens before any transaction opens.
    data = sis.get_student_term_data(student_id=student_id, term_id=term_id)
    pending_aid_total = _pending_aid_total(data)
    tuition_gap = calculate_tuition_gap(data)
    with uow_factory() as uow:
        settings = config.current(uow)
    max_requestable = min(tuition_gap, settings.loan_max_amount)
    return ApplicationStart(
        term_id=term_id,
        tuition_balance=data.tuition_balance,
        pending_aid_total=pending_aid_total,
        tuition_gap=tuition_gap,
        min_amount=settings.loan_min_amount,
        max_requestable=max_requestable,
        payment_deadline=data.payment_deadline,
    )


def submit(
    *,
    uow_factory: UnitOfWorkFactory,
    sis: SisReaderPort,
    clock: Clock,
    student_id: StudentId,
    term_id: TermId,
    requested_amount: Money,
    idempotency_key: IdempotencyKey,
) -> SubmissionResult:
    """Re-read the SIS, revalidate, then in one immediate transaction: insert the application, assess,
    decide (FR-002.2), and on approval reserve funds and generate the agreement; on escalation open a
    review; audit everything. A retry with the same key returns the original result (NFR-001.2)."""
    raise NotImplementedError("applications.submit")


def decide(assessment: EligibilityAssessment) -> DecisionOutcome:
    """Any Fail -> DENIED; else any Escalate -> ESCALATED; else APPROVED (FR-002.2). Pure."""
    raise NotImplementedError("applications.decide")


def denial_reasons(assessment: EligibilityAssessment) -> tuple[str, ...]:
    """The plain-language reason of every rule that returned Fail (FR-002.3). Pure."""
    raise NotImplementedError("applications.denial_reasons")


def get(uow: UnitOfWork, *, application_id: ApplicationId, student_id: StudentId | None) -> LoanApplication:
    """student_id=None only for officer callers; otherwise the application must belong to the student."""
    raise NotImplementedError("applications.get")


def list_for_student(uow: UnitOfWork, *, student_id: StudentId) -> list[LoanApplication]:
    return _load_applications(uow, applications.c.student_id == student_id)


def appeal(
    uow: UnitOfWork,
    *,
    application_id: ApplicationId,
    student_id: StudentId,
    explanation: str | None,
    clock: Clock,
) -> ExceptionReview:
    """One appeal within appeal_window_days of the denial (closed when now > decided_at + window). Opens an
    APPEAL review with the original rule outcomes; does not re-run the rules. Raises ActiveApplicationExists
    if the student has another active application or loan for the term (FR-002.4)."""
    raise NotImplementedError("applications.appeal")


def resolve_review(
    *,
    uow_factory: UnitOfWorkFactory,
    sis: SisReaderPort,
    clock: Clock,
    review_id: ReviewId,
    officer_id: UserId,
    decision: ReviewDecision,
    rationale: str,
) -> Decision:
    """Officer decision. On approve: refuse after the payment deadline, re-read the SIS and recheck the gap
    (FR-003.6), then reserve (refused if the fund cannot cover, FR-003.3), generate the agreement and audit
    the officer, rationale and rule outcomes (FR-003.4), all in one transaction. Deny never calls the SIS."""
    raise NotImplementedError("applications.resolve_review")


def expire_overdue_reviews(*, uow_factory: UnitOfWorkFactory, clock: Clock) -> list[ApplicationId]:
    """Expire open reviews past the payment deadline and deny with "Review not completed before the
    payment deadline." (FR-003.5)."""
    raise NotImplementedError("applications.expire_overdue_reviews")


def expire_unsigned(*, uow_factory: UnitOfWorkFactory, clock: Clock) -> list[ApplicationId]:
    """Expire approved applications whose agreement passed sign_by, and release the reservation (FR-004.3)."""
    raise NotImplementedError("applications.expire_unsigned")
