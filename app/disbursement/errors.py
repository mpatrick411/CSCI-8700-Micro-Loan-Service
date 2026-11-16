from app.kernel import DomainError


class DisbursementNotFound(DomainError):
    code = "disbursement_not_found"


class DisbursementAlreadyExists(DomainError):
    code = "disbursement_already_exists"
