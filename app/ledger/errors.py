from app.kernel import DomainError


class FundNotFound(DomainError):
    code = "fund_not_found"


class FundAlreadySeeded(DomainError):
    """The fund already has a capital entry under a different idempotency key."""

    code = "fund_already_seeded"


class InsufficientFunds(DomainError):
    """Available balance does not cover the reservation (FR-003.3, FR-006.1, NFR-001.1)."""

    code = "fund_insufficient"


class NoActiveReservation(DomainError):
    """release/disburse found no un-converted reservation for the application."""

    code = "fund_no_active_reservation"


class IdempotencyKeyReused(DomainError):
    """The key exists with a different amount or reference (NFR-001.2). Same key, same payload returns the original."""

    code = "fund_idempotency_key_reused"
