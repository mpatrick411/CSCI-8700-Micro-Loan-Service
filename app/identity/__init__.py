"""identity: resolve the current user and enforce the role an endpoint declares (NFR-002.2)."""

from app.identity.errors import Forbidden, Unauthenticated
from app.identity.models import CurrentUser, Role
from app.identity.ports import IdentityProvider
from app.identity.service import DEV_USER_HEADER, get_current_user, require_role, student_id_of

__all__ = [
    "DEV_USER_HEADER",
    "CurrentUser",
    "Forbidden",
    "IdentityProvider",
    "Role",
    "Unauthenticated",
    "get_current_user",
    "require_role",
    "student_id_of",
]
