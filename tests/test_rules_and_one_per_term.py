"""§7 Eligibility rules (FR-002.1–002.3, FR-002.6) and §6 one active application per term (FR-001.6)."""

from __future__ import annotations

from conftest import O1, S1, assert_error, assert_fund, assert_nc, assert_nm, outcomes, reason_of

ALL_PASS = {
    "enrollment": "pass",
    "satisfactory_academic_progress": "pass",
    "fund_availability": "pass",
    "no_overdue_loans": "pass",
}


def start_and_submit(world, requested="600.00", user=S1) -> dict:
    s = world.start(user)
    assert s.status_code == 200, s.text
    r = world.submit(requested, user)
    assert r.status_code == 201, r.text
    return world.application(r.json()["application"]["application_id"], user)


def assert_escalated(world, application: dict) -> None:
    assert application["status"] == "under_review"
    assert application["agreement_id"] is None
    reviews = [rv for rv in world.open_reviews(O1) if rv["application_id"] == application["application_id"]]
    assert len(reviews) == 1 and reviews[0]["kind"] == "escalation"
    assert_fund(world, "10000.00", "0.00", "0.00", "0.00")


# --- Enrollment bands ------------------------------------------------------------------------------


def test_TP_RUL_01(world):
    """6 credits -> Enrollment=Pass; approved."""
    world.sis.set(S1, enrollment_credits=6)
    app = start_and_submit(world)
    assert outcomes(app) == ALL_PASS
    assert app["status"] == "approved"
    assert_fund(world, "9400.00", "600.00", "0.00", "0.00")


def test_TP_RUL_02(world):
    """5 credits -> Enrollment=Escalate; escalated; one open review; F1 unchanged."""
    world.sis.set(S1, enrollment_credits=5)
    app = start_and_submit(world)
    assert outcomes(app) == {**ALL_PASS, "enrollment": "escalate"}
    assert_escalated(world, app)


def test_TP_RUL_03(world):
    """3 credits -> Enrollment=Escalate; escalated."""
    world.sis.set(S1, enrollment_credits=3)
    app = start_and_submit(world)
    assert outcomes(app) == {**ALL_PASS, "enrollment": "escalate"}
    assert_escalated(world, app)


# --- Fund availability -----------------------------------------------------------------------------


def test_TP_RUL_05(make_world):
    """F1 capital $600.00 covers $600.00 -> Fund availability=Pass; approved; F1 = 0 / 600 / 0 / 0."""
    world = make_world(fund_capital="600.00")
    app = start_and_submit(world)
    assert outcomes(app) == ALL_PASS
    assert app["status"] == "approved"
    assert_fund(world, "0.00", "600.00", "0.00", "0.00")


def test_TP_RUL_06(make_world):
    """Pair: TP-RUL-05. F1 capital $599.99 -> Fund availability=Fail; denied [Fund availability]; NM."""
    world = make_world(fund_capital="599.99")
    app = start_and_submit(world)
    assert outcomes(app) == {**ALL_PASS, "fund_availability": "fail"}
    assert app["decisions"][-1]["reasons"] == [reason_of(app, "fund_availability")]
    assert_nm(world, app, ("599.99", "0.00", "0.00", "0.00"))


def test_TP_RUL_08(make_world):
    """4 credits (Escalate) + F1 $599.99 (Fail) -> denied [Fund availability]; no review; NM (FR-002.2 precedence)."""
    world = make_world(fund_capital="599.99")
    world.sis.set(S1, enrollment_credits=4)
    app = start_and_submit(world)
    o = outcomes(app)
    assert o["enrollment"] == "escalate"
    assert o["fund_availability"] == "fail"
    assert app["decisions"][-1]["outcome"] == "denied"
    assert app["decisions"][-1]["reasons"] == [reason_of(app, "fund_availability")]
    assert world.open_reviews(O1) == []
    assert_nm(world, app, ("599.99", "0.00", "0.00", "0.00"))


# --- One active application per term: TP-ONE-06 (control) and TP-ONE-04 (rejection) ---------------
# Both tests have the same shape: a first Fall 2026 application A1, then SIS reports 12 credits and
# S1 submits A2 for $600.00. Only A1's status differs (denied vs escalated).


def test_TP_ONE_06(world):
    """A1 denied (2 credits), not appealed -> A2 accepted and approved; S1 has 2 applications."""
    world.sis.set(S1, enrollment_credits=2)
    a1 = start_and_submit(world)
    assert a1["status"] == "denied"

    world.sis.set(S1, enrollment_credits=12)
    a2 = start_and_submit(world)

    assert a2["status"] == "approved"
    statuses = {a["application_id"]: a["status"] for a in world.applications(S1)}
    assert statuses == {a1["application_id"]: "denied", a2["application_id"]: "approved"}
    assert_fund(world, "9400.00", "600.00", "0.00", "0.00")


def test_TP_ONE_04(world):
    """Pair: TP-ONE-06. A1 escalated (open review) -> A2 submit refused (409); NC."""
    world.sis.set(S1, enrollment_credits=4)
    a1 = start_and_submit(world)
    assert a1["status"] == "under_review"

    world.sis.set(S1, enrollment_credits=12)
    before = world.snapshot()
    r = world.submit("600.00")

    assert_error(r, 409, "application_active_exists")
    assert_nc(world, before)
    assert [a["application_id"] for a in world.applications(S1)] == [a1["application_id"]]
    assert world.application(a1["application_id"])["status"] == "under_review"
