from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.eligibility import EligibilityAssessment, SapStatus
from app.kernel import Actor, AgreementId, ApplicationId, FundId, Money, ReviewId, StudentId, TermId


class ApplicationStatus(StrEnum):
    """Active = UNDER_REVIEW or APPROVED (FR-001.6)."""

    UNDER_REVIEW = "under_review"  # escalated or appealed
    APPROVED = "approved"  # agreement generated; may be signed
    DENIED = "denied"
    EXPIRED = "expired"  # approved but unsigned within the window (FR-004.3)


class DecisionOutcome(StrEnum):
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"


class DecisionSource(StrEnum):
    AUTOMATIC = "automatic"
    OFFICER = "officer"
    REVIEW_EXPIRY = "review_expiry"  # FR-003.5
    SIGNING_EXPIRY = "signing_expiry"  # FR-004.3


@dataclass(frozen=True)
class AidAward:
    award_id: str
    description: str
    amount: Money
    accepted: bool
    disbursed: bool


@dataclass(frozen=True)
class StudentTermData:
    """Everything read from the SIS (FR-001.2). The SIS is the source of truth for these (FR-001.5)."""

    student_id: StudentId
    term_id: TermId
    tuition_balance: Money  # charges minus payments and aid already posted
    aid_awards: tuple[AidAward, ...]
    enrollment_credits: int
    sap_status: SapStatus
    registration_hold: bool
    payment_deadline: date


@dataclass(frozen=True)
class ApplicationStart:
    """What the student sees on starting (AC-01 scenario 1). Nothing is persisted (FR-001.6)."""

    term_id: TermId
    tuition_balance: Money
    pending_aid_total: Money
    tuition_gap: Money
    min_amount: Money
    max_requestable: Money  # min(tuition_gap, loan_max_amount)
    payment_deadline: date


@dataclass(frozen=True)
class AmountValidation:
    ok: bool
    message: str | None  # e.g. "exceeds your tuition gap of $600"


@dataclass(frozen=True)
class Decision:
    outcome: DecisionOutcome
    source: DecisionSource
    reasons: tuple[str, ...]  # plain-language reason for every failed rule on denial (FR-002.3)
    decided_by: Actor
    decided_at: datetime
    rationale: str | None  # officer decisions only
    rule_set_version: str


@dataclass(frozen=True)
class LoanApplication:
    application_id: ApplicationId
    student_id: StudentId
    term_id: TermId
    fund_id: FundId
    requested_amount: Money
    tuition_gap_at_submission: Money
    status: ApplicationStatus
    submitted_at: datetime
    assessment: EligibilityAssessment
    decisions: tuple[Decision, ...]  # oldest first; last is current
    appealed_at: datetime | None
    review_id: ReviewId | None
    agreement_id: AgreementId | None


@dataclass(frozen=True)
class SubmissionResult:
    application: LoanApplication
    decision: Decision
