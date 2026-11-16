"""Shared fixture for the test plan (test_plan.md §0).

Drives the system through the REST API (contracts.md Part 2) with the injected neighbours replaced:
  * container.clock -> FrozenClock  (kernel.Clock protocol; baseline 2026-09-01 09:00 institution time)
  * container.sis   -> FakeSis      (applications.SisReaderPort + disbursement.SisPostingPort; raises
                                      kernel.SisUnavailable on outage, as the port contract says)
The fund F1 is ledger.DEFAULT_FUND_ID, seeded with ledger.seed_fund (contracts.md: "called ... by test
fixtures to set a starting balance").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import ledger
from app.applications import AidAward, StudentTermData
from app.disbursement.ports import SisPostingReceipt
from app.eligibility import SapStatus
from app.identity import DEV_USER_HEADER
from app.kernel import SYSTEM_ACTOR, IdempotencyKey, Money, SisUnavailable, StudentId, TermId
from app.main import create_app

# Spec gap G-17: the institution's time zone is not specified. None of the rows written so far depends on
# the choice; every time in the plan is institution-local.
INSTITUTION_TZ = ZoneInfo("America/Chicago")

S1, S2, S3 = "u-student-1", "u-student-2", "u-student-3"
O1, O2 = "u-officer-1", "u-officer-2"
ADMIN = "u-admin-1"

FALL_2026 = "fall-2026"
F1 = ledger.DEFAULT_FUND_ID

BASELINE_NOW = datetime(2026, 9, 1, 9, 0, 0, tzinfo=INSTITUTION_TZ)


# --------------------------------------------------------------------------------------------------
# Test doubles for injected neighbours
# --------------------------------------------------------------------------------------------------


@dataclass
class FrozenClock:
    """kernel.Clock: now() is tz-aware UTC, today() is the institution-local date."""

    _now: datetime

    def now(self) -> datetime:
        return self._now.astimezone(timezone.utc)

    def today(self) -> date:
        return self._now.astimezone(INSTITUTION_TZ).date()

    def advance(self, by: timedelta) -> datetime:
        if by <= timedelta(0):
            raise ValueError("by must be positive")
        self._now = self._now + by
        return self.now()

    def set_local(self, local: datetime) -> None:
        self._now = local.replace(tzinfo=INSTITUTION_TZ)


def baseline_sis_record() -> dict[str, Any]:
    """§0.1 SIS data per student for Fall 2026. Money as decimal strings, turned into Money on read."""
    return {
        "tuition_balance": "4000.00",
        "aid_awards": [
            {"award_id": "aid-1", "description": "State grant", "amount": "3400.00", "accepted": True, "disbursed": False}
        ],
        "enrollment_credits": 12,
        "sap_status": "Meeting",
        "registration_hold": False,
        "payment_deadline": date(2026, 9, 15),
    }


@dataclass
class FakeSis:
    """In-memory SIS behind both SIS ports. Records are keyed by (seeded user ref, term id) and matched to the
    StudentId the app passes in through the identity provider, so tests never guess student ids."""

    identity: Any
    records: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    outage: bool = False
    read_calls: list[tuple[str, str]] = field(default_factory=list)
    postings: list[dict[str, Any]] = field(default_factory=list)

    def set(self, user_ref: str, term_id: str = FALL_2026, **overrides: Any) -> None:
        record = self.records.get((user_ref, term_id)) or baseline_sis_record()
        record.update(overrides)
        self.records[(user_ref, term_id)] = record

    def _record_for(self, student_id: StudentId, term_id: TermId) -> dict[str, Any] | None:
        for (ref, term), record in self.records.items():
            if term != term_id:
                continue
            user = self.identity.resolve(ref)
            if user is not None and user.student_id == student_id:
                return record
        return None

    # applications.SisReaderPort
    def get_student_term_data(self, *, student_id: StudentId, term_id: TermId) -> StudentTermData:
        self.read_calls.append((student_id, term_id))
        if self.outage:
            raise SisUnavailable("mock SIS outage")
        r = self._record_for(student_id, term_id)
        if r is None:
            raise SisUnavailable("no SIS record")
        return StudentTermData(
            student_id=student_id,
            term_id=term_id,
            tuition_balance=Money.of(r["tuition_balance"]),
            aid_awards=tuple(
                AidAward(
                    award_id=a["award_id"],
                    description=a["description"],
                    amount=Money.of(a["amount"]),
                    accepted=a["accepted"],
                    disbursed=a["disbursed"],
                )
                for a in r["aid_awards"]
            ),
            enrollment_credits=r["enrollment_credits"],
            sap_status=SapStatus(r["sap_status"]),
            registration_hold=r["registration_hold"],
            payment_deadline=r["payment_deadline"],
        )

    # disbursement.SisPostingPort
    def post_disbursement_credit(
        self, *, student_id: StudentId, term_id: TermId, amount: Money, idempotency_key: IdempotencyKey
    ) -> SisPostingReceipt:
        if self.outage:
            raise SisUnavailable("mock SIS outage")
        self.postings.append({"student_id": student_id, "term_id": term_id, "amount": amount, "key": idempotency_key})
        return SisPostingReceipt(sis_transaction_id=f"sis-{len(self.postings)}", posted_at=datetime.now(timezone.utc))


# --------------------------------------------------------------------------------------------------
# World: the running app plus helpers named after contract routes
# --------------------------------------------------------------------------------------------------


def money(value: Any) -> Decimal:
    """JSON money is a decimal string (contracts.md conventions, NFR-001.3)."""
    assert isinstance(value, str), f"money must be a decimal string, got {value!r}"
    return Decimal(value)


class World:
    def __init__(self, client: TestClient, clock: FrozenClock, sis: FakeSis) -> None:
        self.client = client
        self.clock = clock
        self.sis = sis

    # --- HTTP -------------------------------------------------------------------------------------
    def get(self, path: str, user: str):
        return self.client.get(f"/api{path}", headers={DEV_USER_HEADER: user})

    def post(self, path: str, user: str, json: dict, idempotency_key: str | None = None):
        headers = {DEV_USER_HEADER: user}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return self.client.post(f"/api{path}", headers=headers, json=json)

    # --- Student routes ---------------------------------------------------------------------------
    def start(self, user: str = S1, term_id: str = FALL_2026):
        return self.get(f"/terms/{term_id}/application-start", user)

    def validate(self, requested: str, gap: str, user: str = S1):
        return self.post("/applications/validate-amount", user, {"requested_amount": requested, "tuition_gap": gap})

    def submit(self, requested: str, user: str = S1, term_id: str = FALL_2026):
        return self.post(
            "/applications", user, {"term_id": term_id, "requested_amount": requested},
            idempotency_key=f"submit-{uuid.uuid4()}",
        )

    def applications(self, user: str = S1) -> list[dict]:
        r = self.get("/applications", user)
        assert r.status_code == 200, r.text
        return r.json()

    def application(self, application_id: str, user: str = S1) -> dict:
        r = self.get(f"/applications/{application_id}", user)
        assert r.status_code == 200, r.text
        return r.json()

    def loans(self, user: str = S1) -> list[dict]:
        r = self.get("/loans", user)
        assert r.status_code == 200, r.text
        return r.json()

    # --- Officer / shared routes ------------------------------------------------------------------
    def open_reviews(self, officer: str = O1) -> list[dict]:
        r = self.get("/reviews", officer)
        assert r.status_code == 200, r.text
        return r.json()

    def balances(self) -> dict:
        r = self.get(f"/funds/{F1}/balances", O1)
        assert r.status_code == 200, r.text
        return r.json()

    def rule_set_version(self) -> str:
        r = self.get("/config", S1)
        assert r.status_code == 200, r.text
        return r.json()["rule_set"]["version"]

    # --- Composite checks -------------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Everything NC (§0.2) says must not change after a rejected request."""
        return {
            "applications": {u: [(a["application_id"], a["status"]) for a in self.applications(u)] for u in (S1, S2, S3)},
            "loans": {u: [(l["loan_id"], l["status"]) for l in self.loans(u)] for u in (S1, S2, S3)},
            "reviews": [(r["review_id"], r["status"]) for r in self.open_reviews()],
            "balances": self.balances(),
            "sis_postings": len(self.sis.postings),
        }


def assert_fund(world: World, available: str, reserved: str, disbursed: str, repaid: str) -> None:
    """F1 = available / reserved / disbursed / repaid (§0.1)."""
    b = world.balances()
    assert (money(b["available"]), money(b["reserved"]), money(b["disbursed_principal"]), money(b["repaid_principal"])) == (
        Decimal(available), Decimal(reserved), Decimal(disbursed), Decimal(repaid)
    ), b


def assert_error(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()
    assert body["error"] == code, body
    assert isinstance(body.get("message"), str) and body["message"].strip(), body
    return body


def assert_nc(world: World, before: dict) -> None:
    """NC: nothing created, nothing moved, existing records keep their status."""
    assert world.snapshot() == before


def outcomes(application: dict) -> dict[str, str]:
    """{rule name: outcome} from a LoanApplication's EligibilityAssessment; exactly one result per rule."""
    results = application["assessment"]["results"]
    by_rule = {r["rule"]: r["outcome"] for r in results}
    assert len(by_rule) == len(results) == 4, results
    return by_rule


def reason_of(application: dict, rule: str) -> str:
    [result] = [r for r in application["assessment"]["results"] if r["rule"] == rule]
    return result["reason"]


def assert_nm(world: World, application: dict, fund: tuple[str, str, str, str], user: str = S1) -> None:
    """NM: application and assessment stored as denied; no ledger entry, agreement, loan or review."""
    stored = world.application(application["application_id"], user)
    assert stored["status"] == "denied"
    assert stored["decisions"][-1]["outcome"] == "denied"
    assert stored["assessment"]["results"], "assessment must be stored"
    assert stored["agreement_id"] is None
    assert stored["review_id"] is None
    assert [r for r in world.open_reviews() if r["application_id"] == stored["application_id"]] == []
    assert world.loans(user) == []
    assert world.sis.postings == []
    assert_fund(world, *fund)


@pytest.fixture
def make_world(tmp_path, monkeypatch):
    """Factory: make_world(fund_capital="10000.00") -> World on a fresh database (§0.1 baseline)."""
    clients: list[TestClient] = []

    def _make(fund_capital: str = "10000.00") -> World:
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'loans.db'}")
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        client.__enter__()  # runs lifespan -> app.state.container
        clients.append(client)

        container = app.state.container
        clock = FrozenClock(BASELINE_NOW)
        sis = FakeSis(identity=container.identity)
        for user in (S1, S2, S3):
            sis.set(user)
        container.clock = clock
        container.sis = sis

        with container.uow_factory(immediate=True) as uow:
            ledger.seed_fund(
                uow,
                fund_id=F1,
                initial_capital=Money.of(fund_capital),
                idempotency_key=IdempotencyKey("seed-F1"),
                actor=SYSTEM_ACTOR,
                clock=clock,
            )
        return World(client, clock, sis)

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def world(make_world) -> World:
    return make_world()
