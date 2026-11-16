"""agreements: generate, e-sign, store and serve LoanAgreements (FR-004.1, FR-004.2, FR-002.5, NFR-004.1–004.3)."""

from app.agreements.errors import (
    AgreementNotFound,
    AgreementNotPendingSignature,
    AgreementNotSigned,
    ConsentRequired,
    SigningWindowClosed,
)
from app.agreements.models import (
    AgreementStatus,
    ConsentInput,
    ConsentRecord,
    LoanAgreement,
    RenderedDocument,
)
from app.agreements.ports import ESignaturePort, SignatureEvidence
from app.agreements.service import (
    download_signed,
    expire,
    find_unsigned_past_window,
    generate,
    get,
    render_for_review,
    sign,
)

__all__ = [
    "AgreementNotFound",
    "AgreementNotPendingSignature",
    "AgreementNotSigned",
    "AgreementStatus",
    "ConsentInput",
    "ConsentRecord",
    "ConsentRequired",
    "ESignaturePort",
    "LoanAgreement",
    "RenderedDocument",
    "SignatureEvidence",
    "SigningWindowClosed",
    "download_signed",
    "expire",
    "find_unsigned_past_window",
    "generate",
    "get",
    "render_for_review",
    "sign",
]
