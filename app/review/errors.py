from app.kernel import DomainError


class ReviewNotFound(DomainError):
    code = "review_not_found"


class ReviewNotOpen(DomainError):
    """The review was already resolved or expired (lost the compare-and-set)."""

    code = "review_not_open"


class ReviewAlreadyOpen(DomainError):
    """An open review already exists for this application."""

    code = "review_already_open"


class MissingRationale(DomainError):
    """An officer tried to approve or deny without a rationale (FR-003.2)."""

    code = "review_missing_rationale"
