from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.kernel import StudentId, UserId


class Role(StrEnum):
    STUDENT = "student"
    OFFICER = "officer"
    ADMIN = "admin"  # config changes and the demo "advance time" endpoint


@dataclass(frozen=True)
class CurrentUser:
    user_id: UserId
    role: Role
    display_name: str
    student_id: StudentId | None  # set only for Role.STUDENT
