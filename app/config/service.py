from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

from app.config.models import ConfigKey, ConfigSnapshot, RuleSetThresholds
from app.kernel import Actor, AdjustableClock, Clock, UnitOfWork


def current(uow: UnitOfWork) -> ConfigSnapshot:
    raise NotImplementedError("config.current")


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
