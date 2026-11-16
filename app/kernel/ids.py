"""Typed identifiers shared across modules. Plain strings at runtime."""

from typing import NewType

UserId = NewType("UserId", str)
StudentId = NewType("StudentId", str)
TermId = NewType("TermId", str)
FundId = NewType("FundId", str)
ApplicationId = NewType("ApplicationId", str)
ReviewId = NewType("ReviewId", str)
AgreementId = NewType("AgreementId", str)
LoanId = NewType("LoanId", str)
DisbursementId = NewType("DisbursementId", str)
PaymentId = NewType("PaymentId", str)
LedgerEntryId = NewType("LedgerEntryId", str)
IdempotencyKey = NewType("IdempotencyKey", str)

# Who caused a state change: a UserId value or SYSTEM_ACTOR (NFR-003.2).
Actor = NewType("Actor", str)
SYSTEM_ACTOR: Actor = Actor("system")
