from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.kernel import Actor


@dataclass(frozen=True)
class AuditRecord:
    """One append-only, hash-chained record of a state change (NFR-003.2).

    record_hash = SHA-256(prev_hash + canonical JSON of every other field).
    """

    seq: int
    occurred_at: datetime
    actor: Actor
    action: str
    entity_type: str
    entity_id: str
    prior_state: Mapping[str, Any] | None
    new_state: Mapping[str, Any] | None
    rule_set_version: str | None
    prev_hash: str
    record_hash: str


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    records_checked: int
    first_broken_seq: int | None
