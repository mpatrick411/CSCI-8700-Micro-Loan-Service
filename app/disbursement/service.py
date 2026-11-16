from __future__ import annotations

from app.disbursement.models import Disbursement, PostingRunResult
from app.disbursement.ports import SisPostingPort
from app.kernel import Actor, Clock, LoanId, Money, StudentId, TermId, UnitOfWork, UnitOfWorkFactory


def create_pending(
    uow: UnitOfWork,
    *,
    loan_id: LoanId,
    student_id: StudentId,
    term_id: TermId,
    amount: Money,
    actor: Actor,
    clock: Clock,
) -> Disbursement:
    raise NotImplementedError("disbursement.create_pending")


def post_pending(
    *,
    uow_factory: UnitOfWorkFactory,
    sis: SisPostingPort,
    clock: Clock,
) -> PostingRunResult:
    """Post every PENDING disbursement, keyed by disbursement_id. On success record posted_at and call
    repayment.set_due_dates. On SisUnavailable leave it PENDING for the next run. SIS calls are made
    outside any write transaction."""
    raise NotImplementedError("disbursement.post_pending")


def get_for_loan(uow: UnitOfWork, *, loan_id: LoanId, student_id: StudentId) -> Disbursement:
    raise NotImplementedError("disbursement.get_for_loan")
