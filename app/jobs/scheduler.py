"""Each job is a thin wrapper over one domain function, so it can also be called directly in tests."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.disbursement import SisPostingPort
from app.kernel import Clock, UnitOfWorkFactory
from app.repayment import NotificationsPort


def build_scheduler(
    *,
    uow_factory: UnitOfWorkFactory,
    clock: Clock,
    sis: SisPostingPort,
    notifier: NotificationsPort,
) -> BackgroundScheduler:
    """Register the five jobs below on a BackgroundScheduler. Does not start it."""
    raise NotImplementedError("jobs.build_scheduler")


def run_review_expiry(*, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
    """applications.expire_overdue_reviews (FR-003.5)."""
    raise NotImplementedError("jobs.run_review_expiry")


def run_signing_expiry(*, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
    """applications.expire_unsigned (FR-004.3)."""
    raise NotImplementedError("jobs.run_signing_expiry")


def run_disbursement_posting(*, uow_factory: UnitOfWorkFactory, sis: SisPostingPort, clock: Clock) -> None:
    """disbursement.post_pending (NFR-005.3); retries keep the same idempotency key."""
    raise NotImplementedError("jobs.run_disbursement_posting")


def run_due_reminders(*, uow_factory: UnitOfWorkFactory, notifier: NotificationsPort, clock: Clock) -> None:
    """repayment.send_due_reminders (FR-005.3)."""
    raise NotImplementedError("jobs.run_due_reminders")


def run_overdue_flagging(*, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
    """repayment.flag_overdue (FR-006.3)."""
    raise NotImplementedError("jobs.run_overdue_flagging")
