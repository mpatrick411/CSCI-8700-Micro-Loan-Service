"""Money: exact USD amount. Decimal in the domain, integer cents in storage (NFR-001.3)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.kernel.errors import InvalidMoney

_CENT = Decimal("0.01")
# A plain decimal string: optional leading minus, digits, optionally a point and 1 or 2 digits (FR-001.3).
# ASCII digits only; no exponent, no "+", no leading or trailing point.
_PLAIN_DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]{1,2})?")


def _exact_cents(value: Decimal) -> Decimal:
    """`value` as a 2-place Decimal, or InvalidMoney if it is not finite or not a whole number of cents."""
    if not value.is_finite():
        raise InvalidMoney(f"{value} is not a valid amount")
    quantized = value.quantize(_CENT)
    if quantized != value:
        raise InvalidMoney(f"{value} has more than two decimal places")
    return quantized


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0.00"))

    @classmethod
    def of(cls, value: str | int | Decimal) -> Money:
        """Build from a string, int or Decimal. Raises InvalidMoney for floats or more than 2 decimal places."""
        if isinstance(value, Decimal):
            if value.is_finite() and value.as_tuple().exponent < -2:
                raise InvalidMoney(f"{value} has more than two decimal places")
            decimal_value = value
        elif isinstance(value, int) and not isinstance(value, bool):
            decimal_value = Decimal(value)
        elif isinstance(value, str):
            text = value.strip()
            if not _PLAIN_DECIMAL.fullmatch(text):
                raise InvalidMoney(
                    f"{value!r} is not a valid amount: use digits with at most two decimal places, e.g. 600.00"
                )
            try:
                decimal_value = Decimal(text)
            except InvalidOperation:
                raise InvalidMoney(f"{value!r} is not a valid amount") from None
        else:
            raise InvalidMoney(f"{value!r} is not a valid amount: use a string, int or Decimal, never a float")
        return cls(_exact_cents(decimal_value))

    @classmethod
    def from_cents(cls, cents: int) -> Money:
        return cls(Decimal(cents).scaleb(-2).quantize(_CENT))

    def to_cents(self) -> int:
        return int(_exact_cents(self.amount).scaleb(2))

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount - other.amount)

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount >= other.amount

    def is_positive(self) -> bool:
        return self.amount > 0
