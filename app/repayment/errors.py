from app.kernel import DomainError


class LoanNotFound(DomainError):
    """No such loan, or it is not the requesting student's (NFR-002.2)."""

    code = "loan_not_found"


class LoanAlreadyExists(DomainError):
    code = "loan_already_exists"


class LoanNotActive(DomainError):
    code = "loan_not_active"


class DueDatesAlreadySet(DomainError):
    code = "loan_due_dates_already_set"


class InvalidPaymentAmount(DomainError):
    code = "payment_invalid_amount"


class AmountExceedsOutstanding(DomainError):
    code = "payment_exceeds_outstanding"


class PaymentDeclined(DomainError):
    code = "payment_declined"


class AutopayAlreadyEnrolled(DomainError):
    code = "autopay_already_enrolled"
