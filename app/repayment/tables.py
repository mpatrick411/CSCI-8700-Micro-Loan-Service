"""Tables owned by `repayment`. Only app.repayment reads or writes them.

Money is integer cents (NFR-001.3); datetimes are ISO 8601 strings with their UTC offset.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Index, Integer, String, Table

from app.kernel.uow import metadata
from app.repayment.models import LoanStatus

loans = Table(
    "loans",
    metadata,
    Column("loan_id", String, primary_key=True),
    Column("application_id", String, nullable=False, unique=True),
    Column("student_id", String, nullable=False, index=True),
    Column("term_id", String, nullable=False),
    Column("fund_id", String, nullable=False),
    Column("principal_cents", Integer, nullable=False),
    Column("outstanding_cents", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("flagged_for_follow_up", Boolean, nullable=False),  # FR-006.3
    Column("created_at", String, nullable=False),  # ISO 8601 with UTC offset
)

# At most one active Loan per student per term (FR-001.6); a Loan is active until it is fully repaid.
Index(
    "uq_loans_active_per_student_term",
    loans.c.student_id,
    loans.c.term_id,
    unique=True,
    sqlite_where=loans.c.status == LoanStatus.ACTIVE.value,
)
