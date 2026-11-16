"""Base error types. Each module defines its own DomainError subclasses in its errors.py."""


class DomainError(Exception):
    """Base for every expected, user-explainable failure. `web` maps these to HTTP responses."""

    code: str = "domain_error"


class InvalidMoney(DomainError):
    """A value cannot be represented as an exact USD amount (float input, more than 2 decimal places)."""

    code = "invalid_money"


class SisUnavailable(DomainError):
    """The SIS timed out (3 s), had a transport error, or returned incomplete data or unrecognised values such as an
    unknown SAP status (FR-001.4, FR-003.6, NFR-005.2).

    Raised by the SIS adapter for both SIS ports (applications.SisReaderPort, disbursement.SisPostingPort).
    """

    code = "sis_unavailable"
