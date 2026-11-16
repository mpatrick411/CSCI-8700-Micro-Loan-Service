"""§2 AC-02: Automated Loan Eligibility Decisions (refined)."""

from __future__ import annotations

from conftest import O1, S1, assert_fund, assert_nm, money, outcomes, reason_of

ALL_PASS = {
    "enrollment": "pass",
    "satisfactory_academic_progress": "pass",
    "fund_availability": "pass",
    "no_overdue_loans": "pass",
}


def start_and_submit(world, requested="600.00", user=S1) -> dict:
    """Background: started a Fall 2026 application and requested $600.00; then 'When I submit'."""
    s = world.start(user)
    assert s.status_code == 200, s.text
    assert money(s.json()["tuition_gap"]) == money("600.00")
    r = world.submit(requested, user)
    assert r.status_code == 201, r.text
    return r.json()


def test_TP_AC02_01(world):
    """4 credits + 'Meeting' -> escalated; O1's dashboard shows gap, the $3,400 award and only Enrollment (Escalate)."""
    world.sis.set(S1, enrollment_credits=4, sap_status="Meeting")

    result = start_and_submit(world)

    stored = world.application(result["application"]["application_id"])
    assert outcomes(stored) == {**ALL_PASS, "enrollment": "escalate"}
    assert stored["status"] == "under_review"
    assert result["decision"]["outcome"] == "escalated"

    entries = [rv for rv in world.open_reviews(O1) if rv["application_id"] == stored["application_id"]]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["kind"] == "escalation"
    assert entry["status"] == "open"
    assert money(entry["tuition_gap"]) == money("600.00")
    assert len(entry["aid_awards"]) == 1
    assert money(entry["aid_awards"][0]["amount"]) == money("3400.00")
    assert entry["aid_awards"][0]["accepted"] is True
    assert entry["aid_awards"][0]["disbursed"] is False
    assert [(o["rule"], o["outcome"]) for o in entry["rule_outcomes"]] == [("enrollment", "escalate")]

    assert_fund(world, "10000.00", "0.00", "0.00", "0.00")


def test_TP_AC02_02(world):
    """4 credits (Escalate) + 'Suspended' (Fail) -> denied; reasons list only SAP; no review; NM."""
    world.sis.set(S1, enrollment_credits=4, sap_status="Suspended")

    result = start_and_submit(world)

    stored = world.application(result["application"]["application_id"])
    assert result["decision"]["outcome"] == "denied"
    assert stored["status"] == "denied"
    o = outcomes(stored)
    assert o["enrollment"] == "escalate"
    assert o["satisfactory_academic_progress"] == "fail"
    assert result["decision"]["reasons"] == [reason_of(stored, "satisfactory_academic_progress")]
    assert world.open_reviews(O1) == []
    assert_nm(world, stored, ("10000.00", "0.00", "0.00", "0.00"))


def test_TP_AC02_03(world):
    """2 credits + 'Suspended' -> denied; reasons list exactly Enrollment and SAP, each in plain language; NM."""
    world.sis.set(S1, enrollment_credits=2, sap_status="Suspended")

    result = start_and_submit(world)

    stored = world.application(result["application"]["application_id"])
    assert result["decision"]["outcome"] == "denied"
    assert stored["status"] == "denied"
    assert outcomes(stored) == {**ALL_PASS, "enrollment": "fail", "satisfactory_academic_progress": "fail"}

    reasons = result["decision"]["reasons"]
    assert reasons == [reason_of(stored, "enrollment"), reason_of(stored, "satisfactory_academic_progress")]
    for reason, rule in zip(reasons, ("enrollment", "satisfactory_academic_progress")):
        # plain language: a sentence for a person, not the rule's identifier
        assert reason.strip() and " " in reason.strip() and reason.strip() != rule
    assert_nm(world, stored, ("10000.00", "0.00", "0.00", "0.00"))
