"""HTTP client to the mock SIS container. Implements applications.SisReaderPort and disbursement.SisPostingPort.

Turns timeout, transport error, incomplete payloads and unrecognised values (e.g. an unknown SAP status)
into kernel.SisUnavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from app.applications import AidAward, StudentTermData
from app.disbursement import SisPostingReceipt
from app.eligibility import SapStatus
from app.kernel import IdempotencyKey, InvalidMoney, Money, SisUnavailable, StudentId, TermId


def _require(payload: dict[str, Any], key: str, kind: type) -> Any:
    """A required field of the expected JSON type; a missing or mistyped field is incomplete data (FR-001.4)."""
    if key not in payload or payload[key] is None:
        raise SisUnavailable(f"SIS response is missing {key!r}")
    value = payload[key]
    # bool is a subclass of int, so an int field must reject it explicitly.
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise SisUnavailable(f"SIS response field {key!r} has an unexpected type")
    return value


def _money(payload: dict[str, Any], key: str) -> Money:
    raw = payload.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        raise SisUnavailable(f"SIS response is missing or has a non-decimal {key!r}")
    try:
        return Money.of(raw)
    except (InvalidMoney, ArithmeticError, ValueError) as exc:
        raise SisUnavailable(f"SIS response field {key!r} is not a valid amount") from exc


@dataclass
class HttpSisAdapter:
    base_url: str
    timeout_seconds: float = 3.0  # NFR-005.2

    def get_student_term_data(self, *, student_id: StudentId, term_id: TermId) -> StudentTermData:
        url = f"{self.base_url.rstrip('/')}/students/{student_id}/terms/{term_id}"
        try:
            response = httpx.get(url, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:  # timeout or transport error (NFR-005.2, FR-001.4)
            raise SisUnavailable(f"SIS request failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise SisUnavailable(f"SIS answered {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise SisUnavailable("SIS response is not JSON") from exc
        if not isinstance(payload, dict):
            raise SisUnavailable("SIS response is not a JSON object")
        return self._parse_student_term(payload, student_id=student_id, term_id=term_id)

    @staticmethod
    def _parse_student_term(payload: dict[str, Any], *, student_id: StudentId, term_id: TermId) -> StudentTermData:
        """Incomplete data and unrecognised values become SisUnavailable (FR-001.4)."""
        raw_awards = _require(payload, "aid_awards", list)
        awards = []
        for raw in raw_awards:
            if not isinstance(raw, dict):
                raise SisUnavailable("SIS aid award is not a JSON object")
            awards.append(
                AidAward(
                    award_id=_require(raw, "award_id", str),
                    description=_require(raw, "description", str),
                    amount=_money(raw, "amount"),
                    accepted=_require(raw, "accepted", bool),
                    disbursed=_require(raw, "disbursed", bool),
                )
            )
        try:
            sap_status = SapStatus(_require(payload, "sap_status", str))
        except ValueError as exc:  # e.g. a SAP status other than Meeting, Warning or Suspended
            raise SisUnavailable("SIS returned an unrecognised SAP status") from exc
        try:
            payment_deadline = date.fromisoformat(_require(payload, "payment_deadline", str))
        except ValueError as exc:
            raise SisUnavailable("SIS returned an invalid payment deadline") from exc
        return StudentTermData(
            student_id=student_id,
            term_id=term_id,
            tuition_balance=_money(payload, "tuition_balance"),
            aid_awards=tuple(awards),
            enrollment_credits=_require(payload, "enrollment_credits", int),
            sap_status=sap_status,
            registration_hold=_require(payload, "registration_hold", bool),
            payment_deadline=payment_deadline,
        )

    def post_disbursement_credit(
        self,
        *,
        student_id: StudentId,
        term_id: TermId,
        amount: Money,
        idempotency_key: IdempotencyKey,
    ) -> SisPostingReceipt:
        raise NotImplementedError("adapters.HttpSisAdapter.post_disbursement_credit")
