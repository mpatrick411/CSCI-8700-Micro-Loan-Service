from app.kernel import DomainError


class UnknownConfigKey(DomainError):
    code = "config_unknown_key"


class InvalidConfigValue(DomainError):
    """Value has the wrong type or breaks a cross-field constraint (e.g. min > max, escalate >= pass)."""

    code = "config_invalid_value"
