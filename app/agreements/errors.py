from app.kernel import DomainError


class AgreementNotFound(DomainError):
    """No such agreement, or not the requesting student's (NFR-002.2)."""

    code = "agreement_not_found"


class SigningWindowClosed(DomainError):
    """Signing attempted after sign_by (FR-004.3), checked against the Clock at the moment of action."""

    code = "agreement_signing_window_closed"


class AgreementNotPendingSignature(DomainError):
    """Already signed or expired (lost the compare-and-set)."""

    code = "agreement_not_pending_signature"


class ConsentRequired(DomainError):
    """Consent to electronic records or intent to sign was not affirmed (NFR-004.1)."""

    code = "agreement_consent_required"


class AgreementNotSigned(DomainError):
    code = "agreement_not_signed"
