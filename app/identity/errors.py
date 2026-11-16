from app.kernel import DomainError


class Unauthenticated(DomainError):
    """No user, or an unknown user, in the dev header."""

    code = "unauthenticated"


class Forbidden(DomainError):
    """The user's role is not one the endpoint declares, or the record is not theirs (NFR-002.2)."""

    code = "forbidden"
