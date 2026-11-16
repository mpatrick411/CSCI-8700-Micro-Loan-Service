"""Seeded users chosen by the X-Dev-User header or the UI user-switcher. Implements identity.IdentityProvider.

Synthetic users only. Replace with a real SSO/MFA adapter later (NFR-002.3); get_current_user keeps its signature.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.identity import CurrentUser, Role
from app.kernel import StudentId, UserId

SEEDED_USERS: tuple[CurrentUser, ...] = (
    CurrentUser(UserId("u-student-1"), Role.STUDENT, "Sam Student", StudentId("S1001")),
    CurrentUser(UserId("u-student-2"), Role.STUDENT, "Sky Student", StudentId("S1002")),
    CurrentUser(UserId("u-student-3"), Role.STUDENT, "Sol Student", StudentId("S1003")),
    CurrentUser(UserId("u-officer-1"), Role.OFFICER, "Olivia Officer", None),
    CurrentUser(UserId("u-officer-2"), Role.OFFICER, "Oscar Officer", None),
    CurrentUser(UserId("u-admin-1"), Role.ADMIN, "Avery Admin", None),
)


@dataclass
class SeededIdentityProvider:
    users: tuple[CurrentUser, ...] = SEEDED_USERS

    def resolve(self, user_ref: str) -> CurrentUser | None:
        raise NotImplementedError("adapters.SeededIdentityProvider.resolve")

    def list_users(self) -> list[CurrentUser]:
        raise NotImplementedError("adapters.SeededIdentityProvider.list_users")
