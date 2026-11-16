"""§1 AC-01: Submit a Loan Application (refined), with its paired rejections placed next to their controls."""

from __future__ import annotations

from datetime import datetime

from conftest import (
    S1,
    assert_error,
    assert_fund,
    assert_nc,
    assert_nm,
    money,
    outcomes,
    reason_of,
)

ALL_PASS = {
    "enrollment": "pass",
    "satisfactory_academic_progress": "pass",
    "fund_availability": "pass",
    "no_overdue_loans": "pass",
}


def started(world, user=S1) -> dict:
    """'Given I have started a loan application for Fall 2026'."""
    r = world.start(user)
    assert r.status_code == 200, r.text
    return r.json()


# --- TP-AC01-01 (control) and TP-SIS-01 (rejection) ------------------------------------------------


def test_TP_AC01_01(world):
    """Student sees their calculated tuition gap; starting creates no LoanApplication (FR-001.1, 001.3, 001.6)."""
    r = world.start(S1)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["term_id"] == "fall-2026"
    assert money(body["tuition_balance"]) == money("4000.00")
    assert money(body["pending_aid_total"]) == money("3400.00")
    assert money(body["tuition_gap"]) == money("600.00")
    assert money(body["max_requestable"]) == money("600.00")
    assert money(body["min_amount"]) == money("100.00")
    assert body["payment_deadline"] == "2026-09-15"
    assert world.applications(S1) == []


def test_TP_SIS_01(world):
    """Pair: TP-AC01-01. SIS outage at start -> refused with 'try again later'; NC (FR-001.4)."""
    before = world.snapshot()
    world.sis.outage = True

    r = world.start(S1)

    body = assert_error(r, 503, "sis_try_again_later")
    assert "try again later" in body["message"].lower()
    world.sis.outage = False
    assert_nc(world, before)


# --- TP-AC01-02 (control) and TP-AC01-05 (rejection) -----------------------------------------------


def test_TP_AC01_02(world):
    """Eligible student is automatically approved (FR-002.1, 002.2, 002.5, 004.1)."""
    version = world.rule_set_version()
    started(world)

    r = world.submit("600.00")

    assert r.status_code == 201, r.text
    result = r.json()
    application = result["application"]
    decision = result["decision"]

    # Decision
    assert decision["outcome"] == "approved"
    assert decision["source"] == "automatic"
    assert decision["decided_by"] == "system"
    assert datetime.fromisoformat(decision["decided_at"]) == world.clock.now()
    assert decision["reasons"] == []
    assert decision["rule_set_version"] == version

    # Stored application and assessment
    stored = world.application(application["application_id"])
    assert stored["status"] == "approved"
    assert money(stored["requested_amount"]) == money("600.00")
    assert outcomes(stored) == ALL_PASS
    assert stored["assessment"]["rule_set_version"] == version
    assert stored["review_id"] is None
    assert [a["application_id"] for a in world.applications(S1)] == [stored["application_id"]]

    # LoanAgreement pending signature, and the student can review it ("prompted to review and sign")
    assert stored["agreement_id"] is not None
    ra = world.get(f"/agreements/{stored['agreement_id']}", S1)
    assert ra.status_code == 200, ra.text
    agreement = ra.json()
    assert agreement["status"] == "pending_signature"
    assert money(agreement["amount"]) == money("600.00")
    assert agreement["application_id"] == stored["application_id"]
    rd = world.get(f"/agreements/{stored['agreement_id']}/document", S1)
    assert rd.status_code == 200, rd.text
    assert rd.headers["content-type"].startswith("application/pdf")

    # Reservation
    assert_fund(world, "9400.00", "600.00", "0.00", "0.00")
    assert world.loans(S1) == []


def test_TP_AC01_05(world):
    """Pair: TP-AC01-02. $900 exceeds the $600 gap: message shown, submit refused, NC (FR-001.3)."""
    start = started(world)
    before = world.snapshot()

    v = world.validate("900.00", start["tuition_gap"])

    assert v.status_code == 200, v.text
    validation = v.json()
    assert validation["ok"] is False
    assert "exceeds your tuition gap of $600" in validation["message"]

    # "submit is disabled": the API must also refuse the submission
    r = world.submit("900.00")
    body = assert_error(r, 422, "application_amount_out_of_range")
    assert "exceeds your tuition gap of $600" in body["message"]
    assert_nc(world, before)


# --- Decisions other than approval -----------------------------------------------------------------


def test_TP_AC01_03(world):
    """Ineligible student (2 credits) is automatically denied with the Enrollment reason; NM (FR-002.2, 002.3, 002.6)."""
    world.sis.set(S1, enrollment_credits=2)
    started(world)

    r = world.submit("600.00")

    assert r.status_code == 201, r.text
    result = r.json()
    stored = world.application(result["application"]["application_id"])
    assert stored["status"] == "denied"
    assert result["decision"]["outcome"] == "denied"
    assert outcomes(stored) == {**ALL_PASS, "enrollment": "fail"}
    assert result["decision"]["reasons"] == [reason_of(stored, "enrollment")]
    assert stored["decisions"][-1]["reasons"] == [reason_of(stored, "enrollment")]
    assert_nm(world, stored, ("10000.00", "0.00", "0.00", "0.00"))


def test_TP_AC01_04(world):
    """SAP 'Warning' with 12 credits is escalated: one open escalation review, no agreement, no reservation (FR-002.2)."""
    world.sis.set(S1, sap_status="Warning", enrollment_credits=12)
    started(world)

    r = world.submit("600.00")

    assert r.status_code == 201, r.text
    result = r.json()
    stored = world.application(result["application"]["application_id"])
    assert result["decision"]["outcome"] == "escalated"
    assert stored["status"] == "under_review"  # "I see that my application is under review"
    assert outcomes(stored) == {**ALL_PASS, "satisfactory_academic_progress": "escalate"}
    assert stored["agreement_id"] is None

    reviews = [rv for rv in world.open_reviews() if rv["application_id"] == stored["application_id"]]
    assert len(reviews) == 1
    assert reviews[0]["kind"] == "escalation"
    assert reviews[0]["status"] == "open"
    assert stored["review_id"] == reviews[0]["review_id"]

    assert world.loans(S1) == []
    assert_fund(world, "10000.00", "0.00", "0.00", "0.00")
