from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.kernel import Money


class ConfigKey(StrEnum):
    LOAN_MIN_AMOUNT = "loan_min_amount"  # FR-001.3, default $100
    LOAN_MAX_AMOUNT = "loan_max_amount"  # FR-001.3, default $1,500
    APPEAL_WINDOW_DAYS = "appeal_window_days"  # FR-002.4, default 7
    SIGNING_WINDOW_DAYS = "signing_window_days"  # FR-004.3, default 7
    INSTALLMENT_COUNT = "installment_count"  # FR-005.1, default 4
    REMINDER_DAYS_BEFORE_DUE = "reminder_days_before_due"  # FR-005.3, default 3
    OVERDUE_AFTER_DAYS = "overdue_after_days"  # FR-006.3, default 10
    ENROLLMENT_PASS_MIN_CREDITS = "enrollment_pass_min_credits"  # FR-002.6, default 6
    ENROLLMENT_ESCALATE_MIN_CREDITS = "enrollment_escalate_min_credits"  # FR-002.6, default 3


@dataclass(frozen=True)
class RuleSetThresholds:
    """The eligibility thresholds in effect; `version` is recorded on every assessment (FR-002.6)."""

    version: str
    enrollment_pass_min_credits: int
    enrollment_escalate_min_credits: int


@dataclass(frozen=True)
class ConfigSnapshot:
    version: int
    effective_from: datetime
    loan_min_amount: Money
    loan_max_amount: Money
    appeal_window_days: int
    signing_window_days: int
    installment_count: int
    reminder_days_before_due: int
    overdue_after_days: int
    rule_set: RuleSetThresholds
