"""Public service functions of `audit`. Callers pass the UnitOfWork so the record commits with the change (NFR-003.1)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import insert, select

from app.audit.errors import MissingActor
from app.audit.models import AuditRecord, ChainVerification
from app.audit.tables import audit_records
from app.kernel import Actor, Clock, UnitOfWork

# prev_hash of the first record in the chain.
_GENESIS_HASH = "0" * 64


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _record_hash(prev_hash: str, fields: Mapping[str, Any]) -> str:
    """SHA-256(prev_hash + canonical JSON of every field other than prev_hash and record_hash)."""
    return hashlib.sha256((prev_hash + _canonical_json(fields)).encode("utf-8")).hexdigest()


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
    if not actor or not str(actor).strip():
        raise MissingActor("every audit record needs an actor (a user id or 'system')")

    session = uow.session
    last = session.execute(
        select(audit_records.c.seq, audit_records.c.record_hash).order_by(audit_records.c.seq.desc()).limit(1)
    ).first()
    seq = 1 if last is None else last.seq + 1
    prev_hash = _GENESIS_HASH if last is None else last.record_hash

    occurred_at = clock.now()
    prior = dict(prior_state) if prior_state is not None else None
    new = dict(new_state) if new_state is not None else None
    fields = {
        "seq": seq,
        "occurred_at": occurred_at.isoformat(),
        "actor": str(actor),
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "prior_state": prior,
        "new_state": new,
        "rule_set_version": rule_set_version,
    }
    record_hash = _record_hash(prev_hash, fields)

    session.execute(
        insert(audit_records).values(
            seq=seq,
            occurred_at=fields["occurred_at"],
            actor=fields["actor"],
            action=action,
            entity_type=entity_type,
            entity_id=fields["entity_id"],
            prior_state=_canonical_json(prior) if prior is not None else None,
            new_state=_canonical_json(new) if new is not None else None,
            rule_set_version=rule_set_version,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )
    )
    return AuditRecord(
        seq=seq,
        occurred_at=occurred_at,
        actor=Actor(fields["actor"]),
        action=action,
        entity_type=entity_type,
        entity_id=fields["entity_id"],
        prior_state=prior,
        new_state=new,
        rule_set_version=rule_set_version,
        prev_hash=prev_hash,
        record_hash=record_hash,
    )


def records_for(
    uow: UnitOfWork,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> list[AuditRecord]:
    raise NotImplementedError("audit.records_for")


def verify_chain(uow: UnitOfWork) -> ChainVerification:
    raise NotImplementedError("audit.verify_chain")
