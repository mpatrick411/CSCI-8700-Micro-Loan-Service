from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.kernel import Money


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ESCALATE = "escalate"


class RuleName(StrEnum):
    ENROLLMENT = "enrollment"
    SAP = "satisfactory_academic_progress"
    FUND_AVAILABILITY = "fund_availability"
    NO_OVERDUE_LOANS = "no_overdue_loans"


class SapStatus(StrEnum):
    MEETING = "Meeting"
    WARNING = "Warning"
    SUSPENDED = "Suspended"


@dataclass(frozen=True)
class EligibilityInput:
    """Everything a decision depends on. Stored with the assessment so it can be reproduced (NFR-003.4)."""

    requested_amount: Money
    enrollment_credits: int
    sap_status: SapStatus
    fund_available_balance: Money
    has_overdue_installment: bool


@dataclass(frozen=True)
class RuleResult:
    rule: RuleName
    outcome: Outcome
    reason: str  # plain language (FR-002.3)


@dataclass(frozen=True)
class EligibilityAssessment:
    rule_set_version: str
    inputs: EligibilityInput
    results: tuple[RuleResult, ...]  # one per rule, in RULES order
