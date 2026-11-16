"""Public service functions of `applications`.

Functions that call the SIS take a UnitOfWorkFactory so every SIS call happens before the write
transaction opens (architecture.md, "All SIS calls made before the write transaction opens").
"""

from __future__ import annotations

from app.applications.models import (
    AmountValidation,
    ApplicationStart,
    Decision,
    DecisionOutcome,
    LoanApplication,
    StudentTermData,
    SubmissionResult,
)
from app.applications.ports import SisReaderPort
from app.eligibility import EligibilityAssessment
from app.kernel import (
    ApplicationId,
    Clock,
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


def calculate_tuition_gap(data: StudentTermData) -> Money:
    """tuition_balance minus accepted-but-undisbursed aid (FR-001.1). Pure; may be zero or negative."""
    raise NotImplementedError("applications.calculate_tuition_gap")


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
    raise NotImplementedError("applications.start")


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
    raise NotImplementedError("applications.list_for_student")


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
