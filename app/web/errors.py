"""Error mapping for HTTP.

`not_implemented_handler` is skeleton plumbing: any NotImplementedError raised while serving a route
becomes HTTP 501 {"error": "not_implemented", "message": ...}, naming the route's mapped function.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app import agreements, applications, audit, config, disbursement, identity, ledger, repayment, review
from app.kernel import DomainError, InvalidMoney, SisUnavailable

# contracts.md Part 2: unauthenticated -> 401, not found -> 404, forbidden -> 403, validation/rule refusals -> 422,
# state conflicts (lost compare-and-set, active application exists) -> 409, TryAgainLater -> 503.
_UNAUTHENTICATED, _FORBIDDEN, _NOT_FOUND, _CONFLICT, _REFUSED, _TRY_AGAIN_LATER = 401, 403, 404, 409, 422, 503
_INTERNAL = 500

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    # kernel
    InvalidMoney: _REFUSED,
    SisUnavailable: _TRY_AGAIN_LATER,  # normally mapped to TryAgainLater by `applications` first
    # identity
    identity.Unauthenticated: _UNAUTHENTICATED,
    identity.Forbidden: _FORBIDDEN,
    # applications
    applications.TryAgainLater: _TRY_AGAIN_LATER,
    applications.NoTuitionGap: _REFUSED,
    applications.AmountOutOfRange: _REFUSED,
    applications.ActiveApplicationExists: _CONFLICT,
    applications.ApplicationNotFound: _NOT_FOUND,
    applications.ApplicationNotDenied: _CONFLICT,
    applications.AppealWindowClosed: _REFUSED,
    applications.AppealAlreadyUsed: _CONFLICT,
    applications.PaymentDeadlinePassed: _REFUSED,
    applications.AmountExceedsRecalculatedGap: _REFUSED,
    applications.FundCannotCover: _REFUSED,
    # review
    review.ReviewNotFound: _NOT_FOUND,
    review.ReviewNotOpen: _CONFLICT,
    review.ReviewAlreadyOpen: _CONFLICT,
    review.MissingRationale: _REFUSED,
    # ledger
    ledger.FundNotFound: _NOT_FOUND,
    ledger.FundAlreadySeeded: _CONFLICT,
    ledger.InsufficientFunds: _REFUSED,
    ledger.NoActiveReservation: _CONFLICT,
    ledger.IdempotencyKeyReused: _REFUSED,
    # repayment
    repayment.LoanNotFound: _NOT_FOUND,
    repayment.LoanAlreadyExists: _CONFLICT,
    repayment.LoanNotActive: _CONFLICT,
    repayment.DueDatesAlreadySet: _CONFLICT,
    repayment.InvalidPaymentAmount: _REFUSED,
    repayment.AmountExceedsOutstanding: _REFUSED,
    repayment.PaymentDeclined: _REFUSED,
    repayment.AutopayAlreadyEnrolled: _CONFLICT,
    # disbursement
    disbursement.DisbursementNotFound: _NOT_FOUND,
    disbursement.DisbursementAlreadyExists: _CONFLICT,
    # agreements
    agreements.AgreementNotFound: _NOT_FOUND,
    agreements.SigningWindowClosed: _REFUSED,
    agreements.AgreementNotPendingSignature: _CONFLICT,
    agreements.ConsentRequired: _REFUSED,
    agreements.AgreementNotSigned: _CONFLICT,
    # config
    config.UnknownConfigKey: _REFUSED,
    config.InvalidConfigValue: _REFUSED,
    # audit: raised only by a caller that forgot the actor, never by a client request
    audit.MissingActor: _INTERNAL,
}

# Used when an error carries no user text of its own.
_DEFAULT_MESSAGE_BY_STATUS: dict[int, str] = {
    _UNAUTHENTICATED: "Sign in to continue.",
    _FORBIDDEN: "You do not have access to this page.",
    _NOT_FOUND: "We could not find that record.",
    _CONFLICT: "This request conflicts with the record's current state.",
    _REFUSED: "This request cannot be accepted.",
    _TRY_AGAIN_LATER: "The student information system is unavailable right now. Please try again later.",
    _INTERNAL: "Something went wrong on our side.",
}


async def not_implemented_handler(request: Request, exc: Exception) -> JSONResponse:
    route = request.scope.get("route")
    function_name = getattr(route, "name", None) or "unknown"
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "message": f"{request.method} {request.url.path} maps to {function_name}, which is not implemented yet.",
        },
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Registered by create_app for every DomainError: the (status, body) from to_http_error as JSON."""
    status, body = to_http_error(exc)
    return JSONResponse(status_code=status, content=body)


def to_http_error(exc: DomainError) -> tuple[int, dict[str, str]]:
    """Map a DomainError to (HTTP status, {"error": exc.code, "message": user-facing text}).

    E.g. TryAgainLater -> 503 "try again later" (FR-001.4, FR-003.6); AmountOutOfRange -> 422 with the
    "exceeds your tuition gap of $600" text (AC-01); Forbidden -> 403; *NotFound -> 404.
    The message is the error's own text; an error raised without text gets its status's default.
    """
    status = _status_for(type(exc))
    message = str(exc).strip() or _DEFAULT_MESSAGE_BY_STATUS[status]
    return status, {"error": exc.code, "message": message}


def _status_for(error_type: type[DomainError]) -> int:
    """The mapped status of the error class or its nearest mapped base; unmapped errors are bugs (500)."""
    for cls in error_type.__mro__:
        status = _STATUS_BY_ERROR.get(cls)
        if status is not None:
            return status
    return _INTERNAL
