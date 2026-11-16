from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config.models import ConfigKey, ConfigSnapshot, RuleSetThresholds
from app.config.tables import config_versions
from app.kernel import Actor, AdjustableClock, Clock, Money, UnitOfWork

# In effect while no version is stored (contracts.md, config.current; test_plan.md §0.1 "Config version v1").
_DEFAULTS = ConfigSnapshot(
    version=1,
    effective_from=datetime(1970, 1, 1, tzinfo=timezone.utc),
    loan_min_amount=Money.of("100.00"),
    loan_max_amount=Money.of("1500.00"),
    appeal_window_days=7,
    signing_window_days=7,
    installment_count=4,
    reminder_days_before_due=3,
    overdue_after_days=10,
    rule_set=RuleSetThresholds(
        version="v1",
        enrollment_pass_min_credits=6,
        enrollment_escalate_min_credits=3,
    ),
)


def current(uow: UnitOfWork) -> ConfigSnapshot:
    row = uow.session.execute(select(config_versions).order_by(config_versions.c.version.desc()).limit(1)).first()
    if row is None:
        return _DEFAULTS
    return ConfigSnapshot(
        version=row.version,
        effective_from=datetime.fromisoformat(row.effective_from),
        loan_min_amount=Money.from_cents(row.loan_min_amount_cents),
        loan_max_amount=Money.from_cents(row.loan_max_amount_cents),
        appeal_window_days=row.appeal_window_days,
        signing_window_days=row.signing_window_days,
        installment_count=row.installment_count,
        reminder_days_before_due=row.reminder_days_before_due,
        overdue_after_days=row.overdue_after_days,
        rule_set=RuleSetThresholds(
            version=row.rule_set_version,
            enrollment_pass_min_credits=row.enrollment_pass_min_credits,
            enrollment_escalate_min_credits=row.enrollment_escalate_min_credits,
        ),
    )


def rule_set(uow: UnitOfWork) -> RuleSetThresholds:
    raise NotImplementedError("config.rule_set")


def update(
    uow: UnitOfWork,
    *,
    changes: Mapping[ConfigKey, str],
    actor: Actor,
    clock: Clock,
) -> ConfigSnapshot:
    """Write a new config version (and a new rule-set version if a threshold changed) and audit it."""
    raise NotImplementedError("config.update")


def advance_clock(
    uow: UnitOfWork,
    *,
    clock: AdjustableClock,
    by: timedelta,
    actor: Actor,
) -> datetime:
    """Admin demo convenience: move the Clock forward and audit the move like a config change."""
    raise NotImplementedError("config.advance_clock")
