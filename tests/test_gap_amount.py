"""§3 Tuition gap (FR-001.1) and §4 requested amount validation (FR-001.3). Each control precedes its rejection."""

from __future__ import annotations

from conftest import S1, assert_error, assert_fund, assert_nc, money


def start_ok(world) -> dict:
    r = world.start(S1)
    assert r.status_code == 200, r.text
    return r.json()


def assert_accepted_and_approved(world, requested: str, gap: str, fund: tuple[str, str, str, str]) -> dict:
    """'Accepted' (§4): validation passes, the submission is taken, and with baseline data it is approved."""
    v = world.validate(requested, gap)
    assert v.status_code == 200, v.text
    assert v.json()["ok"] is True
    r = world.submit(requested)
    assert r.status_code == 201, r.text
    application = world.application(r.json()["application"]["application_id"])
    assert application["status"] == "approved"
    assert money(application["requested_amount"]) == money(requested)
    assert application["agreement_id"] is not None
    assert_fund(world, *fund)
    return application


def assert_rejected(world, requested: str, gap: str) -> dict:
    """Rejected by FR-001.3: validation says not ok; a direct submit is refused with 422; NC."""
    before = world.snapshot()
    v = world.validate(requested, gap)
    assert v.status_code == 200, v.text
    assert v.json()["ok"] is False
    assert v.json()["message"]
    body = assert_error(world.submit(requested), 422, "application_amount_out_of_range")
    assert_nc(world, before)
    return body


# --- §3 Gap: minimum loan boundary -----------------------------------------------------------------


def test_TP_GAP_01(world):
    """Gap exactly $100.00 (the minimum): start allowed; gap $100.00, max requestable $100.00."""
    world.sis.set(S1, tuition_balance="3500.00")

    body = start_ok(world)

    assert money(body["tuition_gap"]) == money("100.00")
    assert money(body["max_requestable"]) == money("100.00")
    assert world.applications(S1) == []


def test_TP_GAP_02(world):
    """Pair: TP-GAP-01. Gap $99.99 (< minimum): start refused; NC."""
    world.sis.set(S1, tuition_balance="3499.99")
    before = world.snapshot()

    r = world.start(S1)

    assert_error(r, 422, "application_no_tuition_gap")
    assert_nc(world, before)


# --- §4 Amount: at most the gap --------------------------------------------------------------------


def test_TP_AMT_01(world):
    """$600.00 = gap: accepted; approved; F1 = 9,400 / 600 / 0 / 0."""
    start = start_ok(world)
    assert_accepted_and_approved(world, "600.00", start["tuition_gap"], ("9400.00", "600.00", "0.00", "0.00"))


def test_TP_AMT_02(world):
    """Pair: TP-AMT-01. $600.01 > gap: rejected, 'exceeds gap of $600'; NC."""
    start = start_ok(world)

    body = assert_rejected(world, "600.01", start["tuition_gap"])

    assert "exceeds your tuition gap of $600" in body["message"]
    assert "exceeds your tuition gap of $600" in world.validate("600.01", start["tuition_gap"]).json()["message"]


# --- §4 Amount: at least the minimum ---------------------------------------------------------------


def test_TP_AMT_03(world):
    """$100.00 = minimum: accepted; approved; F1 = 9,900 / 100 / 0 / 0."""
    start = start_ok(world)
    assert_accepted_and_approved(world, "100.00", start["tuition_gap"], ("9900.00", "100.00", "0.00", "0.00"))


def test_TP_AMT_04(world):
    """Pair: TP-AMT-03. $99.99 < minimum: rejected; NC. (Message wording undefined in the spec: rejection only.)"""
    start = start_ok(world)
    assert_rejected(world, "99.99", start["tuition_gap"])


# --- §4 Amount: at most the configured maximum -----------------------------------------------------


def test_TP_AMT_05(world):
    """Gap $1,600.00; $1,500.00 = maximum: accepted; approved; F1 = 8,500 / 1,500 / 0 / 0."""
    world.sis.set(S1, tuition_balance="5000.00")
    start = start_ok(world)
    assert money(start["tuition_gap"]) == money("1600.00")
    assert_accepted_and_approved(world, "1500.00", start["tuition_gap"], ("8500.00", "1500.00", "0.00", "0.00"))


def test_TP_AMT_06(world):
    """Pair: TP-AMT-05. Gap $1,600.00; $1,500.01 > maximum: rejected; NC."""
    world.sis.set(S1, tuition_balance="5000.00")
    start = start_ok(world)
    assert money(start["tuition_gap"]) == money("1600.00")
    assert_rejected(world, "1500.01", start["tuition_gap"])
