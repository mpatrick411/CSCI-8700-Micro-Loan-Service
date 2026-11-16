"""Financial Aid Officer routes (FR-003, FR-006, NFR-001.4, NFR-003)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app import applications, audit, ledger, repayment, review
from app.kernel import FundId, ReviewId
from app.web.deps import ContainerDep, OfficerOrAdmin, OfficerUser
from app.web.schemas import ResolveReviewRequest

router = APIRouter(tags=["officer"])


@router.get("/reviews", name="review.list_open")
def list_open_reviews(user: OfficerUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return review.list_open(uow)


@router.get("/reviews/{review_id}", name="review.get")
def get_review(review_id: str, user: OfficerUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return review.get(uow, review_id=ReviewId(review_id))


@router.post("/reviews/{review_id}/resolution", name="applications.resolve_review")
def resolve_review(review_id: str, body: ResolveReviewRequest, user: OfficerUser, c: ContainerDep):
    return applications.resolve_review(
        uow_factory=c.uow_factory,
        sis=c.sis,
        clock=c.clock,
        review_id=ReviewId(review_id),
        officer_id=user.user_id,
        decision=body.decision,
        rationale=body.rationale,
    )


@router.get("/officer/loans/flagged", name="repayment.list_flagged_loans")
def list_flagged_loans(user: OfficerUser, c: ContainerDep):
    with c.uow_factory() as uow:
        return repayment.list_flagged_loans(uow)


@router.get("/funds/{fund_id}/balances", name="ledger.balances")
def fund_balances(fund_id: str, user: OfficerOrAdmin, c: ContainerDep):
    with c.uow_factory() as uow:
        return ledger.balances(uow, fund_id=FundId(fund_id))


@router.get("/funds/{fund_id}/invariant", name="ledger.verify_invariant")
def fund_invariant(fund_id: str, user: OfficerOrAdmin, c: ContainerDep):
    with c.uow_factory() as uow:
        return ledger.verify_invariant(uow, fund_id=FundId(fund_id))


@router.get("/audit/records", name="audit.records_for")
def audit_records(
    user: OfficerOrAdmin,
    c: ContainerDep,
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
):
    with c.uow_factory() as uow:
        return audit.records_for(uow, entity_type=entity_type, entity_id=entity_id)


@router.get("/audit/verify", name="audit.verify_chain")
def audit_verify(user: OfficerOrAdmin, c: ContainerDep):
    with c.uow_factory() as uow:
        return audit.verify_chain(uow)
