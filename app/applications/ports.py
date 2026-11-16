"""SIS read port, owned by `applications`. Adapter: app.adapters.sis_http.HttpSisAdapter (3 s timeout)."""

from __future__ import annotations

from typing import Protocol

from app.applications.models import StudentTermData
from app.kernel import StudentId, TermId


class SisReaderPort(Protocol):
    def get_student_term_data(self, *, student_id: StudentId, term_id: TermId) -> StudentTermData:
        """Raises kernel.SisUnavailable on timeout, transport error, incomplete payload or unrecognised values."""
        ...
