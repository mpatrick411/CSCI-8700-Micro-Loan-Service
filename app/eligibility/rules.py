"""The four EligibilityRules of FR-002.6, one class each. Thresholds come from config.RuleSetThresholds."""

from __future__ import annotations

from typing import ClassVar, Protocol

from app.config import RuleSetThresholds
from app.eligibility.models import EligibilityInput, RuleName, RuleResult


class EligibilityRule(Protocol):
    name: ClassVar[RuleName]

    def evaluate(self, inputs: EligibilityInput, thresholds: RuleSetThresholds) -> RuleResult: ...


class EnrollmentRule:
    """>= pass_min credits -> Pass; >= escalate_min -> Escalate; otherwise Fail. Defaults 6 / 3."""

    name: ClassVar[RuleName] = RuleName.ENROLLMENT

    def evaluate(self, inputs: EligibilityInput, thresholds: RuleSetThresholds) -> RuleResult:
        raise NotImplementedError("eligibility.EnrollmentRule.evaluate")


class SapRule:
    """Meeting -> Pass; Warning -> Escalate; Suspended -> Fail."""

    name: ClassVar[RuleName] = RuleName.SAP

    def evaluate(self, inputs: EligibilityInput, thresholds: RuleSetThresholds) -> RuleResult:
        raise NotImplementedError("eligibility.SapRule.evaluate")


class FundAvailabilityRule:
    """Available balance >= requested -> Pass; otherwise Fail. Never Escalate."""

    name: ClassVar[RuleName] = RuleName.FUND_AVAILABILITY

    def evaluate(self, inputs: EligibilityInput, thresholds: RuleSetThresholds) -> RuleResult:
        raise NotImplementedError("eligibility.FundAvailabilityRule.evaluate")


class NoOverdueLoansRule:
    """No overdue installment -> Pass; otherwise Fail."""

    name: ClassVar[RuleName] = RuleName.NO_OVERDUE_LOANS

    def evaluate(self, inputs: EligibilityInput, thresholds: RuleSetThresholds) -> RuleResult:
        raise NotImplementedError("eligibility.NoOverdueLoansRule.evaluate")


RULES: tuple[EligibilityRule, ...] = (
    EnrollmentRule(),
    SapRule(),
    FundAvailabilityRule(),
    NoOverdueLoansRule(),
)
