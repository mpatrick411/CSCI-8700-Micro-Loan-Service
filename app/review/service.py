from __future__ import annotations

from datetime import date

from app.kernel import Actor, ApplicationId, Clock, Money, ReviewId, StudentId, TermId, UnitOfWork, UserId
from app.review.models import AidAwardView, ExceptionReview, ReviewDecision, ReviewKind, RuleOutcomeView


def open(
    uow: UnitOfWork,
    *,
    kind: ReviewKind,
    application_id: ApplicationId,
    student_id: StudentId,
    term_id: TermId,
    payment_deadline: date,
    requested_amount: Money,
    tuition_gap: Money,
    pending_aid_total: Money,
    aid_awards: tuple[AidAwardView, ...],
    rule_outcomes: tuple[RuleOutcomeView, ...],
    student_explanation: str | None,
    actor: Actor,
    clock: Clock,
) -> ExceptionReview:
    raise NotImplementedError("review.open")


def get(uow: UnitOfWork, *, review_id: ReviewId) -> ExceptionReview:
    raise NotImplementedError("review.get")


def list_open(uow: UnitOfWork) -> list[ExceptionReview]:
    """Every OPEN review (escalations and appeals), sorted by payment_deadline, earliest first; ties by
    earliest opened_at (FR-003.1)."""
    raise NotImplementedError("review.list_open")


def resolve(
    uow: UnitOfWork,
    *,
    review_id: ReviewId,
    decision: ReviewDecision,
    rationale: str,
    officer_id: UserId,
    clock: Clock,
) -> ExceptionReview:
    """Compare-and-set OPEN -> RESOLVED. Rationale must not be blank or whitespace-only (FR-003.2)."""
    raise NotImplementedError("review.resolve")


def find_expired(uow: UnitOfWork, *, clock: Clock) -> list[ExceptionReview]:
    """OPEN reviews whose payment_deadline is before clock.today(); the deadline date itself is still open (FR-003.5)."""
    raise NotImplementedError("review.find_expired")


def expire(uow: UnitOfWork, *, review_id: ReviewId, actor: Actor, clock: Clock) -> ExceptionReview:
    """Compare-and-set OPEN -> EXPIRED."""
    raise NotImplementedError("review.expire")
