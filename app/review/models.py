from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.kernel import ApplicationId, Money, ReviewId, StudentId, TermId, UserId


class ReviewKind(StrEnum):
    ESCALATION = "escalation"
    APPEAL = "appeal"


class ReviewStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    DENY = "deny"


@dataclass(frozen=True)
class RuleOutcomeView:
    """A rule outcome as the officer sees it. `review` keeps its own copy so it does not depend on `eligibility`."""

    rule: str
    outcome: str
    reason: str


@dataclass(frozen=True)
class AidAwardView:
    """An aid award as the officer sees it (FR-003.1). `review` keeps its own copy so it does not depend on `applications`."""

    award_id: str
    description: str
    amount: Money
    accepted: bool
    disbursed: bool


@dataclass(frozen=True)
class ExceptionReview:
    review_id: ReviewId
    kind: ReviewKind
    status: ReviewStatus
    application_id: ApplicationId
    student_id: StudentId
    term_id: TermId
    payment_deadline: date  # dashboard sort key (FR-003.1) and expiry point (FR-003.5)
    requested_amount: Money
    tuition_gap: Money  # shown on the dashboard (FR-003 story)
    pending_aid_total: Money  # "current awards" on the dashboard
    aid_awards: tuple[AidAwardView, ...]  # each current AidAward, shown on the dashboard (FR-003.1)
    rule_outcomes: tuple[RuleOutcomeView, ...]  # original outcomes; appeals do not re-run rules (FR-002.4)
    student_explanation: str | None  # appeals only
    opened_at: datetime
    resolved_at: datetime | None
    resolved_by: UserId | None
    decision: ReviewDecision | None
    rationale: str | None
