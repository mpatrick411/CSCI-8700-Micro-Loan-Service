"""Money: exact USD amount. Decimal in the domain, integer cents in storage (NFR-001.3)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal

    @classmethod
    def zero(cls) -> Money:
        raise NotImplementedError("kernel.Money.zero")

    @classmethod
    def of(cls, value: str | int | Decimal) -> Money:
        """Build from a string, int or Decimal. Raises InvalidMoney for floats or more than 2 decimal places."""
        raise NotImplementedError("kernel.Money.of")

    @classmethod
    def from_cents(cls, cents: int) -> Money:
        raise NotImplementedError("kernel.Money.from_cents")

    def to_cents(self) -> int:
        raise NotImplementedError("kernel.Money.to_cents")

    def __add__(self, other: Money) -> Money:
        raise NotImplementedError("kernel.Money.__add__")

    def __sub__(self, other: Money) -> Money:
        raise NotImplementedError("kernel.Money.__sub__")

    def __lt__(self, other: Money) -> bool:
        raise NotImplementedError("kernel.Money.__lt__")

    def __le__(self, other: Money) -> bool:
        raise NotImplementedError("kernel.Money.__le__")

    def __gt__(self, other: Money) -> bool:
        raise NotImplementedError("kernel.Money.__gt__")

    def __ge__(self, other: Money) -> bool:
        raise NotImplementedError("kernel.Money.__ge__")

    def is_positive(self) -> bool:
        raise NotImplementedError("kernel.Money.is_positive")
