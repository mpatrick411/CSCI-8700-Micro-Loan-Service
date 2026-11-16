from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.kernel import FundId, IdempotencyKey, LedgerEntryId, Money

# The prototype has exactly one LoanFund (architecture.md: multiple funds not handled).
DEFAULT_FUND_ID: FundId = FundId("fund-main")


class LedgerAccount(StrEnum):
    CAPITAL = "capital"  # source of initial capital
    AVAILABLE = "available"
    RESERVED = "reserved"
    DISBURSED_PRINCIPAL = "disbursed_principal"


class EntryKind(StrEnum):
    CAPITAL = "capital"  # CAPITAL -> AVAILABLE
    RESERVE = "reserve"  # AVAILABLE -> RESERVED
    RELEASE = "release"  # RESERVED -> AVAILABLE
    DISBURSE = "disburse"  # RESERVED -> DISBURSED_PRINCIPAL
    REPAYMENT = "repayment"  # DISBURSED_PRINCIPAL -> AVAILABLE


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: LedgerEntryId
    fund_id: FundId
    kind: EntryKind
    debit_account: LedgerAccount
    credit_account: LedgerAccount
    amount: Money
    reference_id: str  # application, loan or payment id
    idempotency_key: IdempotencyKey  # unique (NFR-001.2)
    occurred_at: datetime


@dataclass(frozen=True)
class FundBalances:
    fund_id: FundId
    initial_capital: Money
    available: Money
    reserved: Money
    disbursed_principal: Money  # total ever disbursed; repayments do not reduce it (repaid_principal holds those)
    repaid_principal: Money


@dataclass(frozen=True)
class InvariantReport:
    """NFR-001.4: available == initial capital - active reservations - disbursed principal + repaid principal."""

    fund_id: FundId
    expected_available: Money
    actual_available: Money
    discrepancy: Money
    ok: bool
