"""Tables owned by `ledger`. Only app.ledger reads or writes them.

Append-only double-entry entries; balances are derived from them. The idempotency key is unique (NFR-001.2).
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table

from app.kernel.uow import metadata

ledger_entries = Table(
    "ledger_entries",
    metadata,
    Column("entry_id", String, primary_key=True),
    Column("fund_id", String, nullable=False, index=True),
    Column("kind", String, nullable=False),
    Column("debit_account", String, nullable=False),  # the account the amount moves into
    Column("credit_account", String, nullable=False),  # the account the amount moves out of
    Column("amount_cents", Integer, nullable=False),
    Column("reference_id", String, nullable=False),
    Column("idempotency_key", String, nullable=False, unique=True),
    Column("occurred_at", String, nullable=False),  # ISO 8601 with UTC offset
)
