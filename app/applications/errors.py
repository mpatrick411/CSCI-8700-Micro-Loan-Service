from app.kernel import DomainError


class TryAgainLater(DomainError):
    """The SIS was unavailable or returned incomplete or unrecognised data (FR-001.4, FR-003.6)."""

    code = "sis_try_again_later"


class NoTuitionGap(DomainError):
    """The calculated gap is less than the configured minimum loan amount (FR-001.1)."""

    code = "application_no_tuition_gap"


class AmountOutOfRange(DomainError):
    """Above the gap, above the configured max, or below the configured min (FR-001.3)."""

    code = "application_amount_out_of_range"


class ActiveApplicationExists(DomainError):
    """The student already has an active application or loan for the term (FR-001.6)."""

    code = "application_active_exists"


class ApplicationNotFound(DomainError):
    """No such application, or not the requesting student's (NFR-002.2)."""

    code = "application_not_found"


class ApplicationNotDenied(DomainError):
    code = "application_not_denied"


class AppealWindowClosed(DomainError):
    code = "application_appeal_window_closed"


class AppealAlreadyUsed(DomainError):
    code = "application_appeal_already_used"


class PaymentDeadlinePassed(DomainError):
    """Officer approval attempted after the term payment deadline (FR-003.5)."""

    code = "application_payment_deadline_passed"


class AmountExceedsRecalculatedGap(DomainError):
    """Officer approval refused: requested amount > freshly recalculated gap (FR-003.6)."""

    code = "application_amount_exceeds_recalculated_gap"


class FundCannotCover(DomainError):
    """Officer approval refused: the fund cannot cover the amount (FR-003.3, FR-006.1)."""

    code = "application_fund_cannot_cover"
