"""Public service functions of `audit`. Callers pass the UnitOfWork so the record commits with the change (NFR-003.1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.audit.models import AuditRecord, ChainVerification
from app.kernel import Actor, Clock, UnitOfWork


def append(
    uow: UnitOfWork,
    *,
    actor: Actor,
    action: str,
    entity_type: str,
    entity_id: str,
    prior_state: Mapping[str, Any] | None,
    new_state: Mapping[str, Any] | None,
    rule_set_version: str | None,
    clock: Clock,
) -> AuditRecord:
    raise NotImplementedError("audit.append")


def records_for(
    uow: UnitOfWork,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> list[AuditRecord]:
    raise NotImplementedError("audit.records_for")


def verify_chain(uow: UnitOfWork) -> ChainVerification:
    raise NotImplementedError("audit.verify_chain")
