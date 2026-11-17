"""Injectable Clock. No module reads system time directly (architecture.md, "Time")."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

# The spec does not name the institution's time zone (test_plan G-17); resolved as plan.md DQ-8.
INSTITUTION_TZ = ZoneInfo("America/Chicago")


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
        return datetime.now(timezone.utc) + self.offset

    def today(self) -> date:
        return self.now().astimezone(INSTITUTION_TZ).date()

    def advance(self, by: timedelta) -> datetime:
        """Move the clock forward by `by` (must be positive). Returns the new now()."""
        raise NotImplementedError("kernel.AdjustableClock.advance")
