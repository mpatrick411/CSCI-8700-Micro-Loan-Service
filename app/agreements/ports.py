"""E-signature port, owned by `agreements`. Adapter: app.adapters.esign_mock.ClickToSignAdapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.agreements.models import ConsentInput, ConsentRecord, LoanAgreement, RenderedDocument


@dataclass(frozen=True)
class SignatureEvidence:
    signed_document: RenderedDocument  # includes its SHA-256
    consent: ConsentRecord
    signed_at: datetime


class ESignaturePort(Protocol):
    def render(self, agreement: LoanAgreement) -> RenderedDocument:
        """Unsigned PDF for review."""
        ...

    def capture(
        self,
        *,
        agreement: LoanAgreement,
        consent: ConsentInput,
        signed_at: datetime,
    ) -> SignatureEvidence: ...
