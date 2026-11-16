from __future__ import annotations

from datetime import datetime

from app.kernel import (
    Actor,
    ApplicationId,
    Clock,
    FundId,
    IdempotencyKey,
    LoanId,
    Money,
    StudentId,
    TermId,
    UnitOfWork,
)
from app.repayment.models import (
    AutopayEnrollment,
    Installment,
    Loan,
    Payment,
    PaymentMethodToken,
    RepaymentSchedule,
)
from app.repayment.ports import NotificationsPort, PaymentsPort


def split_installments(principal: Money, count: int) -> tuple[Money, ...]:
    """Equal installments; remainder cents go to the final one (FR-005.1). Pure."""
    raise NotImplementedError("repayment.split_installments")


def create_loan(
    uow: UnitOfWork,
    *,
    application_id: ApplicationId,
    student_id: StudentId,
    term_id: TermId,
    fund_id: FundId,
    principal: Money,
    actor: Actor,
    clock: Clock,
) -> Loan:
    """Create the Loan and its RepaymentSchedule with amounts and no due dates (FR-005.1)."""
    raise NotImplementedError("repayment.create_loan")


def set_due_dates(
    uow: UnitOfWork,
    *,
    loan_id: LoanId,
    posted_at: datetime,
    actor: Actor,
    clock: Clock,
) -> RepaymentSchedule:
    """First installment due 30 calendar days after the institution-local date of posted_at; each later one
    due 30 days after the previous (FR-005.1)."""
    raise NotImplementedError("repayment.set_due_dates")


def get_loan(uow: UnitOfWork, *, loan_id: LoanId, student_id: StudentId | None) -> Loan:
    """student_id=None only for officer callers; otherwise the loan must belong to the student."""
    raise NotImplementedError("repayment.get_loan")


def list_loans(uow: UnitOfWork, *, student_id: StudentId) -> list[Loan]:
    raise NotImplementedError("repayment.list_loans")


def get_schedule(uow: UnitOfWork, *, loan_id: LoanId, student_id: StudentId) -> RepaymentSchedule:
    raise NotImplementedError("repayment.get_schedule")


def has_active_loan(uow: UnitOfWork, *, student_id: StudentId, term_id: TermId) -> bool:
    raise NotImplementedError("repayment.has_active_loan")


def has_overdue_installment(uow: UnitOfWork, *, student_id: StudentId, clock: Clock) -> bool:
    """Computed from due dates and the clock, not only from the job's flag (FR-006.3)."""
    raise NotImplementedError("repayment.has_overdue_installment")


def make_payment(
    uow: UnitOfWork,
    *,
    loan_id: LoanId,
    student_id: StudentId,
    amount: Money,
    method_token: PaymentMethodToken,
    idempotency_key: IdempotencyKey,
    payments: PaymentsPort,
    actor: Actor,
    clock: Clock,
) -> Payment:
    """Charge via the processor, apply to the earliest unpaid installment first, credit the origin fund
    (FR-005.2, FR-006.2)."""
    raise NotImplementedError("repayment.make_payment")


def enroll_autopay(
    uow: UnitOfWork,
    *,
    loan_id: LoanId,
    student_id: StudentId,
    method_token: PaymentMethodToken,
    payments: PaymentsPort,
    actor: Actor,
    clock: Clock,
) -> AutopayEnrollment:
    raise NotImplementedError("repayment.enroll_autopay")


def send_due_reminders(uow: UnitOfWork, *, notifier: NotificationsPort, clock: Clock) -> list[Installment]:
    """Remind once per unpaid installment, reminder_days_before_due calendar days before due (FR-005.3)."""
    raise NotImplementedError("repayment.send_due_reminders")


def flag_overdue(uow: UnitOfWork, *, clock: Clock) -> list[Loan]:
    """Mark installments unpaid more than overdue_after_days past due as OVERDUE and flag their loans (FR-006.3)."""
    raise NotImplementedError("repayment.flag_overdue")


def list_flagged_loans(uow: UnitOfWork) -> list[Loan]:
    raise NotImplementedError("repayment.list_flagged_loans")
