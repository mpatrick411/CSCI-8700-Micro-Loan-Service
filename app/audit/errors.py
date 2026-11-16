from app.kernel import DomainError


class MissingActor(DomainError):
    """append() was called without an actor (NFR-003.2)."""

    code = "audit_missing_actor"
