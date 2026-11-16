"""Tables owned by `review`. Only app.review reads or writes them.

Money is integer cents (NFR-001.3). Dates are ISO dates; datetimes are ISO 8601 strings in UTC with their
offset, so ordering by the stored text is ordering by time. `aid_awards` and `rule_outcomes` hold the
submission snapshot as JSON arrays: all four rule outcomes are stored; reads filter them (DQ-4).
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table, Text

from app.kernel.uow import metadata

exception_reviews = Table(
    "exception_reviews",
    metadata,
    Column("review_id", String, primary_key=True),
    Column("kind", String, nullable=False),
    Column("status", String, nullable=False, index=True),
    Column("application_id", String, nullable=False, index=True),
    Column("student_id", String, nullable=False),
    Column("term_id", String, nullable=False),
    Column("payment_deadline", String, nullable=False),  # ISO date
    Column("requested_amount_cents", Integer, nullable=False),
    Column("tuition_gap_cents", Integer, nullable=False),
    Column("pending_aid_total_cents", Integer, nullable=False),
    # [{"award_id", "description", "amount" (2-place decimal string), "accepted", "disbursed"}, ...]
    Column("aid_awards", Text, nullable=False),
    Column("rule_outcomes", Text, nullable=False),  # [{"rule", "outcome", "reason"}, ...]
    Column("student_explanation", Text, nullable=True),
    Column("opened_at", String, nullable=False),
    Column("resolved_at", String, nullable=True),
    Column("resolved_by", String, nullable=True),
    Column("decision", String, nullable=True),
    Column("rationale", Text, nullable=True),
)
