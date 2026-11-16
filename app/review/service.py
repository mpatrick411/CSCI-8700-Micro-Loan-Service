from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from app.kernel import Actor, ApplicationId, Clock, Money, ReviewId, StudentId, TermId, UnitOfWork, UserId
from app.review.models import (
    AidAwardView,
    ExceptionReview,
    ReviewDecision,
    ReviewKind,
    ReviewStatus,
    RuleOutcomeView,
)
from app.review.tables import exception_reviews

# --- Storage mapping (rows of review/tables.py -> domain objects) ----------------------------------


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _review_from_row(row: Any) -> ExceptionReview:
    return ExceptionReview(
        review_id=ReviewId(row.review_id),
        kind=ReviewKind(row.kind),
        status=ReviewStatus(row.status),
        application_id=ApplicationId(row.application_id),
        student_id=StudentId(row.student_id),
        term_id=TermId(row.term_id),
        payment_deadline=date.fromisoformat(row.payment_deadline),
        requested_amount=Money.from_cents(row.requested_amount_cents),
        tuition_gap=Money.from_cents(row.tuition_gap_cents),
        pending_aid_total=Money.from_cents(row.pending_aid_total_cents),
        aid_awards=tuple(
            AidAwardView(
                award_id=a["award_id"],
                description=a["description"],
                amount=Money.of(a["amount"]),
                accepted=a["accepted"],
                disbursed=a["disbursed"],
            )
            for a in json.loads(row.aid_awards)
        ),
        rule_outcomes=tuple(
            RuleOutcomeView(rule=o["rule"], outcome=o["outcome"], reason=o["reason"])
            for o in json.loads(row.rule_outcomes)
        ),
        student_explanation=row.student_explanation,
        opened_at=datetime.fromisoformat(row.opened_at),
        resolved_at=_parse_datetime(row.resolved_at),
        resolved_by=UserId(row.resolved_by) if row.resolved_by is not None else None,
        decision=ReviewDecision(row.decision) if row.decision is not None else None,
        rationale=row.rationale,
    )


# --- Public service functions --------------------------------------------------------------------


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
    rows = uow.session.execute(
        select(exception_reviews)
        .where(exception_reviews.c.status == ReviewStatus.OPEN.value)
        .order_by(
            exception_reviews.c.payment_deadline,
            exception_reviews.c.opened_at,
            exception_reviews.c.review_id,
        )
    ).all()
    return [_review_from_row(row) for row in rows]


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
