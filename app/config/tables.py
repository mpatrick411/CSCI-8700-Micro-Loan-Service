"""Tables owned by `config`. Only app.config reads or writes them.

One row per configuration version; the highest `version` is in effect. No row means the defaults (v1).
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table

from app.kernel.uow import metadata

config_versions = Table(
    "config_versions",
    metadata,
    Column("version", Integer, primary_key=True, autoincrement=False),
    Column("effective_from", String, nullable=False),  # ISO 8601 with UTC offset
    Column("loan_min_amount_cents", Integer, nullable=False),
    Column("loan_max_amount_cents", Integer, nullable=False),
    Column("appeal_window_days", Integer, nullable=False),
    Column("signing_window_days", Integer, nullable=False),
    Column("installment_count", Integer, nullable=False),
    Column("reminder_days_before_due", Integer, nullable=False),
    Column("overdue_after_days", Integer, nullable=False),
    Column("rule_set_version", String, nullable=False),
    Column("enrollment_pass_min_credits", Integer, nullable=False),
    Column("enrollment_escalate_min_credits", Integer, nullable=False),
)
