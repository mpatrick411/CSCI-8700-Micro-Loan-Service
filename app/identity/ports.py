"""Identity port, owned by `identity`. Prototype adapter: app.adapters.identity_seeded.SeededIdentityProvider."""

from __future__ import annotations

from typing import Protocol

from app.identity.models import CurrentUser


class IdentityProvider(Protocol):
    def resolve(self, user_ref: str) -> CurrentUser | None:
        """Return the user for a credential reference (dev header value now; SSO subject later), or None."""
        ...

    def list_users(self) -> list[CurrentUser]:
        """Users offered by the dev user-switcher."""
        ...
