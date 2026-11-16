"""Mock SIS service: `uvicorn mock_sis.main:app --port 8001`.

Serves synthetic balances, aid awards, credits, SAP status, holds and deadlines (set per student and term
with PUT for test fixtures); accepts disbursement
postings deduplicated by idempotency key; toggles simulate outage, latency and incomplete data.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class DisbursementCreditRequest(BaseModel):
    student_id: str
    term_id: str
    amount: Decimal


class AidAwardRecord(BaseModel):
    award_id: str
    description: str
    amount: Decimal
    accepted: bool
    disbursed: bool


class StudentTermRecord(BaseModel):
    """Synthetic SIS data for one student and term. Test fixtures set it with PUT before a test."""

    tuition_balance: Decimal
    aid_awards: list[AidAwardRecord]
    enrollment_credits: int
    sap_status: str  # sent as-is, so tests can send an unrecognised value (FR-001.4)
    registration_hold: bool
    payment_deadline: str  # ISO date


class Toggles(BaseModel):
    outage: bool = False
    latency_ms: int = 0
    incomplete_data: bool = False


app = FastAPI(title="Mock SIS", version="0.1.0-skeleton")


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: Exception) -> JSONResponse:
    route = request.scope.get("route")
    name = getattr(route, "name", None) or "unknown"
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "message": f"{request.method} {request.url.path} maps to {name}, which is not implemented yet.",
        },
    )


@app.get("/students/{student_id}/terms/{term_id}", name="mock_sis.get_student_term")
def get_student_term(student_id: str, term_id: str) -> dict[str, object]:
    raise NotImplementedError("mock_sis.get_student_term")


@app.put("/students/{student_id}/terms/{term_id}", name="mock_sis.set_student_term")
def set_student_term(student_id: str, term_id: str, body: StudentTermRecord) -> StudentTermRecord:
    raise NotImplementedError("mock_sis.set_student_term")


@app.post("/disbursement-credits", name="mock_sis.post_disbursement_credit")
def post_disbursement_credit(
    body: DisbursementCreditRequest, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]
) -> dict[str, object]:
    raise NotImplementedError("mock_sis.post_disbursement_credit")


@app.put("/toggles", name="mock_sis.set_toggles")
def set_toggles(body: Toggles) -> Toggles:
    raise NotImplementedError("mock_sis.set_toggles")
