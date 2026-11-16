"""Tables owned by `applications`. Only app.applications reads or writes them.

`applications.assessment` holds the EligibilityAssessment, with its full input snapshot, as canonical JSON
(NFR-003.4): {"rule_set_version", "inputs": {...}, "results": [{"rule", "outcome", "reason"}, ...]}.
Money inside it is a 2-place decimal string. Decisions are kept in their own table, oldest first by `seq`.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text

from app.kernel.uow import metadata

applications = Table(
    "applications",
    metadata,
    Column("application_id", String, primary_key=True),
    Column("student_id", String, nullable=False, index=True),
    Column("term_id", String, nullable=False),
    Column("fund_id", String, nullable=False),
    Column("requested_amount_cents", Integer, nullable=False),
    Column("tuition_gap_cents", Integer, nullable=False),  # gap at submission
    Column("status", String, nullable=False),
    Column("submitted_at", String, nullable=False),  # ISO 8601 with UTC offset
    Column("assessment", Text, nullable=False),
    Column("appealed_at", String, nullable=True),
    Column("review_id", String, nullable=True),
    Column("agreement_id", String, nullable=True),
    Column("idempotency_key", String, nullable=False, unique=True),
)

application_decisions = Table(
    "application_decisions",
    metadata,
    Column("application_id", String, ForeignKey("applications.application_id"), primary_key=True),
    Column("seq", Integer, primary_key=True, autoincrement=False),
    Column("outcome", String, nullable=False),
    Column("source", String, nullable=False),
    Column("reasons", Text, nullable=False),  # JSON array of strings
    Column("decided_by", String, nullable=False),
    Column("decided_at", String, nullable=False),  # ISO 8601 with UTC offset
    Column("rationale", Text, nullable=True),
    Column("rule_set_version", String, nullable=False),
)
