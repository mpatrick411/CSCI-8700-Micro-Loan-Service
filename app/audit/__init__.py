"""audit: append hash-chained AuditRecords and verify the chain (FR-003.4, NFR-003.1–003.4)."""

from app.audit.errors import MissingActor
from app.audit.models import AuditRecord, ChainVerification
from app.audit.service import append, records_for, verify_chain

__all__ = ["AuditRecord", "ChainVerification", "MissingActor", "append", "records_for", "verify_chain"]
