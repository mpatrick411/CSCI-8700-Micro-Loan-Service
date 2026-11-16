"""Every write takes an idempotency key: a repeat with the same key returns the original entry (NFR-001.2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select

from app import audit
from app.kernel import (
    Actor,
    ApplicationId,
    Clock,
    FundId,
    IdempotencyKey,
    LedgerEntryId,
    LoanId,
    Money,
    PaymentId,
    UnitOfWork,
)
from app.ledger.errors import FundAlreadySeeded, FundNotFound, IdempotencyKeyReused
from app.ledger.models import EntryKind, FundBalances, InvariantReport, LedgerAccount, LedgerEntry
from app.ledger.tables import ledger_entries


def _entry_from_row(row: Any) -> LedgerEntry:
    return LedgerEntry(
        entry_id=LedgerEntryId(row.entry_id),
        fund_id=FundId(row.fund_id),
        kind=EntryKind(row.kind),
        debit_account=LedgerAccount(row.debit_account),
        credit_account=LedgerAccount(row.credit_account),
        amount=Money.from_cents(row.amount_cents),
        reference_id=row.reference_id,
        idempotency_key=IdempotencyKey(row.idempotency_key),
        occurred_at=datetime.fromisoformat(row.occurred_at),
    )


def _entry_by_key(uow: UnitOfWork, idempotency_key: IdempotencyKey) -> LedgerEntry | None:
    row = uow.session.execute(
        select(ledger_entries).where(ledger_entries.c.idempotency_key == idempotency_key)
    ).first()
    return _entry_from_row(row) if row is not None else None


def _insert_entry(
    uow: UnitOfWork,
    *,
    fund_id: FundId,
    kind: EntryKind,
    from_account: LedgerAccount,
    to_account: LedgerAccount,
    amount: Money,
    reference_id: str,
    idempotency_key: IdempotencyKey,
    clock: Clock,
) -> LedgerEntry:
    """Append one entry moving `amount` from `from_account` (credited) to `to_account` (debited)."""
    entry = LedgerEntry(
        entry_id=LedgerEntryId(f"le-{uuid.uuid4().hex}"),
        fund_id=fund_id,
        kind=kind,
        debit_account=to_account,
        credit_account=from_account,
        amount=amount,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
        occurred_at=clock.now(),
    )
    uow.session.execute(
        insert(ledger_entries).values(
            entry_id=entry.entry_id,
            fund_id=entry.fund_id,
            kind=entry.kind.value,
            debit_account=entry.debit_account.value,
            credit_account=entry.credit_account.value,
            amount_cents=entry.amount.to_cents(),
            reference_id=entry.reference_id,
            idempotency_key=entry.idempotency_key,
            occurred_at=entry.occurred_at.isoformat(),
        )
    )
    return entry


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
    existing = _entry_by_key(uow, idempotency_key)
    if existing is not None:
        if existing.kind == EntryKind.CAPITAL and existing.fund_id == fund_id and existing.amount == initial_capital:
            return existing  # replay of the same seed (NFR-001.2)
        raise IdempotencyKeyReused(f"idempotency key {idempotency_key!r} was already used for a different entry")

    already_seeded = uow.session.execute(
        select(ledger_entries.c.entry_id).where(
            ledger_entries.c.fund_id == fund_id, ledger_entries.c.kind == EntryKind.CAPITAL.value
        )
    ).first()
    if already_seeded is not None:
        raise FundAlreadySeeded(f"fund {fund_id!r} already has its initial capital")

    entry = _insert_entry(
        uow,
        fund_id=fund_id,
        kind=EntryKind.CAPITAL,
        from_account=LedgerAccount.CAPITAL,
        to_account=LedgerAccount.AVAILABLE,
        amount=initial_capital,
        reference_id=fund_id,
        idempotency_key=idempotency_key,
        clock=clock,
    )
    audit.append(
        uow,
        actor=actor,
        action="fund.seeded",
        entity_type="fund",
        entity_id=fund_id,
        prior_state=None,
        new_state={
            "entry_id": entry.entry_id,
            "kind": entry.kind.value,
            "initial_capital": str(initial_capital.amount),
            "idempotency_key": idempotency_key,
        },
        rule_set_version=None,
        clock=clock,
    )
    return entry


def available_balance(uow: UnitOfWork, *, fund_id: FundId) -> Money:
    raise NotImplementedError("ledger.available_balance")


def balances(uow: UnitOfWork, *, fund_id: FundId) -> FundBalances:
    """Every figure is derived from the fund's entries (NFR-001.4). Raises FundNotFound if the fund has none."""
    rows = uow.session.execute(
        select(
            ledger_entries.c.kind,
            ledger_entries.c.debit_account,
            ledger_entries.c.credit_account,
            ledger_entries.c.amount_cents,
        ).where(ledger_entries.c.fund_id == fund_id)
    ).all()
    if not rows:
        raise FundNotFound(f"There is no loan fund {fund_id!r}.")

    # Net cents held by each account: entries moving money in, minus entries moving it out.
    held = {account: 0 for account in LedgerAccount}
    capital_cents = repaid_cents = 0
    for row in rows:
        held[LedgerAccount(row.debit_account)] += row.amount_cents
        held[LedgerAccount(row.credit_account)] -= row.amount_cents
        kind = EntryKind(row.kind)
        if kind == EntryKind.CAPITAL:
            capital_cents += row.amount_cents
        elif kind == EntryKind.REPAYMENT:
            repaid_cents += row.amount_cents

    return FundBalances(
        fund_id=fund_id,
        initial_capital=Money.from_cents(capital_cents),
        available=Money.from_cents(held[LedgerAccount.AVAILABLE]),
        reserved=Money.from_cents(held[LedgerAccount.RESERVED]),
        disbursed_principal=Money.from_cents(held[LedgerAccount.DISBURSED_PRINCIPAL]),
        repaid_principal=Money.from_cents(repaid_cents),
    )


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
