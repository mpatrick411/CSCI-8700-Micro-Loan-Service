from __future__ import annotations

from app.config import RuleSetThresholds
from app.eligibility.models import EligibilityAssessment, EligibilityInput


def assess(inputs: EligibilityInput, thresholds: RuleSetThresholds) -> EligibilityAssessment:
    """Evaluate every rule in RULES. Pure: same inputs and thresholds always give the same assessment."""
    raise NotImplementedError("eligibility.assess")
