"""Tables owned by `audit`. Only app.audit reads or writes them.

The table is append-only: SQLite triggers created with it abort any UPDATE or DELETE (NFR-003.3).
"""

from __future__ import annotations

from sqlalchemy import DDL, Column, Integer, String, Table, Text, event

from app.kernel.uow import metadata

audit_records = Table(
    "audit_records",
    metadata,
    Column("seq", Integer, primary_key=True, autoincrement=False),
    Column("occurred_at", String, nullable=False),  # ISO 8601 with UTC offset
    Column("actor", String, nullable=False),
    Column("action", String, nullable=False),
    Column("entity_type", String, nullable=False),
    Column("entity_id", String, nullable=False),
    Column("prior_state", Text, nullable=True),  # canonical JSON
    Column("new_state", Text, nullable=True),  # canonical JSON
    Column("rule_set_version", String, nullable=True),
    Column("prev_hash", String(64), nullable=False),
    Column("record_hash", String(64), nullable=False, unique=True),
)

event.listen(
    audit_records,
    "after_create",
    DDL(
        "CREATE TRIGGER audit_records_no_update BEFORE UPDATE ON audit_records "
        "BEGIN SELECT RAISE(ABORT, 'audit records are append-only'); END"
    ),
)
event.listen(
    audit_records,
    "after_create",
    DDL(
        "CREATE TRIGGER audit_records_no_delete BEFORE DELETE ON audit_records "
        "BEGIN SELECT RAISE(ABORT, 'audit records are append-only'); END"
    ),
)
