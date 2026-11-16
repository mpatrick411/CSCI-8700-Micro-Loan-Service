"""Injectable Clock. No module reads system time directly (architecture.md, "Time")."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current instant, timezone-aware UTC."""
        ...

    def today(self) -> date:
        """Current date in the institution's local calendar."""
        ...


@dataclass
class SystemClock:
    """Real wall-clock time."""

    def now(self) -> datetime:
        raise NotImplementedError("kernel.SystemClock.now")

    def today(self) -> date:
        raise NotImplementedError("kernel.SystemClock.today")


@dataclass
class AdjustableClock:
    """System time plus a movable offset. Used by tests and by the admin "advance time" endpoint."""

    offset: timedelta = field(default_factory=timedelta)

    def now(self) -> datetime:
        raise NotImplementedError("kernel.AdjustableClock.now")

    def today(self) -> date:
        raise NotImplementedError("kernel.AdjustableClock.today")

    def advance(self, by: timedelta) -> datetime:
        """Move the clock forward by `by` (must be positive). Returns the new now()."""
        raise NotImplementedError("kernel.AdjustableClock.advance")
