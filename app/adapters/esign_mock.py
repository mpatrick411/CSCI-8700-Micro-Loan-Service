"""In-process click-to-sign. Implements agreements.ESignaturePort: renders a PDF, records consent, SHA-256 hash."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.agreements import ConsentInput, LoanAgreement, RenderedDocument, SignatureEvidence


@dataclass
class ClickToSignAdapter:
    def render(self, agreement: LoanAgreement) -> RenderedDocument:
        raise NotImplementedError("adapters.ClickToSignAdapter.render")

    def capture(
        self,
        *,
        agreement: LoanAgreement,
        consent: ConsentInput,
        signed_at: datetime,
    ) -> SignatureEvidence:
        raise NotImplementedError("adapters.ClickToSignAdapter.capture")
