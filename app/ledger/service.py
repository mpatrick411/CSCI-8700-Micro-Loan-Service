"""Every write takes an idempotency key: a repeat with the same key returns the original entry (NFR-001.2)."""

from __future__ import annotations

from app.kernel import (
    Actor,
    ApplicationId,
    Clock,
    FundId,
    IdempotencyKey,
    LoanId,
    Money,
    PaymentId,
    UnitOfWork,
)
from app.ledger.models import FundBalances, InvariantReport, LedgerEntry


def seed_fund(
    uow: UnitOfWork,
    *,
    fund_id: FundId,
    initial_capital: Money,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    clock: Clock,
) -> LedgerEntry:
    """Create the fund with its initial capital: one CAPITAL entry, CAPITAL -> AVAILABLE, audited (NFR-001.4).
    Used at startup for fund-main and by test fixtures to set a fund's starting balance."""
    raise NotImplementedError("ledger.seed_fund")


def available_balance(uow: UnitOfWork, *, fund_id: FundId) -> Money:
    raise NotImplementedError("ledger.available_balance")


def balances(uow: UnitOfWork, *, fund_id: FundId) -> FundBalances:
    raise NotImplementedError("ledger.balances")


def reserve(
    uow: UnitOfWork,
    *,
    fund_id: FundId,
    application_id: ApplicationId,
    amount: Money,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    clock: Clock,
) -> LedgerEntry:
    """Must run inside an immediate UnitOfWork so check-and-reserve is atomic (NFR-001.1)."""
    raise NotImplementedError("ledger.reserve")


def release(
    uow: UnitOfWork,
    *,
    fund_id: FundId,
    application_id: ApplicationId,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    clock: Clock,
) -> LedgerEntry:
    raise NotImplementedError("ledger.release")


def disburse(
    uow: UnitOfWork,
    *,
    fund_id: FundId,
    application_id: ApplicationId,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    clock: Clock,
) -> LedgerEntry:
    """Convert the application's reservation into disbursed principal (FR-002.5)."""
    raise NotImplementedError("ledger.disburse")


def credit_repayment(
    uow: UnitOfWork,
    *,
    fund_id: FundId,
    loan_id: LoanId,
    payment_id: PaymentId,
    amount: Money,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    clock: Clock,
) -> LedgerEntry:
    raise NotImplementedError("ledger.credit_repayment")


def verify_invariant(uow: UnitOfWork, *, fund_id: FundId) -> InvariantReport:
    raise NotImplementedError("ledger.verify_invariant")
