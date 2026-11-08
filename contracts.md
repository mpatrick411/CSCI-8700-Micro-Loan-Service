# Contracts: Tuition Gap Micro-Loan Service (skeleton)

Every function below exists in code with this exact signature and raises `NotImplementedError`. Types live in each module's `models.py`, errors in `errors.py`, ports in `ports.py`.

## Conventions

- **Injected, never read directly.** `uow: UnitOfWork` (the transaction, passed by the caller so state change and AuditRecord commit together, NFR-003.1), `uow_factory: UnitOfWorkFactory` (for functions that call the SIS first and must open the write transaction only afterwards), `clock: Clock`, and one port per external system. No module reads system time.
- **`immediate=True`** on a unit of work means `BEGIN IMMEDIATE` (NFR-001.1). Every money-moving function must run in one.
- **Actor.** Every write takes `actor: Actor` (a `UserId` value or `SYSTEM_ACTOR`) and records it (NFR-003.2).
- **Idempotency.** Money-moving writes take an `IdempotencyKey`. A repeat with the same key and payload returns the original result; the same key with a different payload raises `IdempotencyKeyReused` (NFR-001.2).
- **Ownership.** A `student_id` parameter scopes the read or write to that student. A record owned by someone else is reported as *not found*, not *forbidden*, so its existence is not revealed (NFR-002.2). `student_id: StudentId | None` accepts `None` only from officer callers.
- **Errors.** All expected failures subclass `kernel.DomainError` and carry a `code`. `web.to_http_error` maps them to HTTP. Anything else is a bug.
- **Money.** `kernel.Money` (Decimal) in the domain, integer cents in storage. JSON carries decimal strings such as `"600.00"`.

---

## Part 1: Module functions

### kernel

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `Money.of(value: str \| int \| Decimal) -> Money` | Exact amount | `InvalidMoney` (float, >2 dp) | NFR-001.3 | — |
| `Money.from_cents(cents: int) -> Money` / `Money.to_cents() -> int` | Conversion to/from storage | — | NFR-001.3 | — |
| `Money.zero() -> Money`, `+`, `-`, `<`, `<=`, `>`, `>=`, `is_positive() -> bool` | Exact arithmetic and comparison | — | NFR-001.3 | — |
| `Clock.now() -> datetime` / `Clock.today() -> date` (Protocol; `SystemClock`, `AdjustableClock`) | UTC instant / institution-local date | — | all time-based FRs | — |
| `AdjustableClock.advance(by: timedelta) -> datetime` | New `now()` | `ValueError` if `by` ≤ 0 | admin "advance time" (preference) | — |
| `UnitOfWork` (Protocol): `session`, `__enter__`, `__exit__`, `commit()`, `rollback()` | Commit on clean exit, rollback on exception | SQLAlchemy errors propagate | NFR-001.1, NFR-003.1 | — |
| `UnitOfWorkFactory.__call__(*, immediate: bool = False) -> UnitOfWork` (`SqliteUnitOfWorkFactory(database_url)`) | New unit of work | — | NFR-001.1 | database URL |

Also in kernel: typed ids (`StudentId`, `TermId`, `ApplicationId`, … , `Actor`, `SYSTEM_ACTOR`), `DomainError`, and `SisUnavailable`, the single error the SIS adapter raises for timeout, transport error or incomplete data.

### audit

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `append(uow, *, actor, action: str, entity_type: str, entity_id: str, prior_state: Mapping \| None, new_state: Mapping \| None, rule_set_version: str \| None, clock) -> AuditRecord` | Record appended with `seq`, `prev_hash`, `record_hash = SHA-256(prev_hash + canonical JSON)` | `MissingActor` | NFR-003.1, NFR-003.2, FR-003.4 | uow, clock |
| `records_for(uow, *, entity_type: str \| None = None, entity_id: str \| None = None) -> list[AuditRecord]` | Matching records, `seq` order | — | NFR-003.4 | uow |
| `verify_chain(uow) -> ChainVerification` | `ok`, `records_checked`, `first_broken_seq` | — (a broken chain is a result, not an error) | NFR-003.3 (tamper-evidence) | uow |

The table is protected by SQLite triggers that block UPDATE and DELETE (NFR-003.3); there is no update or delete function.

### config

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `current(uow) -> ConfigSnapshot` | Latest version. Defaults: min $100, max $1,500, appeal 7 d, signing 7 d, 4 installments, overdue 10 d, enrollment 6/3 credits. Reminder days has no spec default and must be seeded | — | FR-001.3, FR-002.4, FR-004.3, FR-005.1, FR-005.3, FR-006.3 | uow |
| `rule_set(uow) -> RuleSetThresholds` | Thresholds plus `version` | — | FR-002.6 | uow |
| `update(uow, *, changes: Mapping[ConfigKey, str], actor, clock) -> ConfigSnapshot` | New version (and new rule-set version if a threshold changed), audited | `UnknownConfigKey`, `InvalidConfigValue` (bad type, min > max, escalate ≥ pass) | FR-002.6, NFR-003.1 | uow, clock |
| `advance_clock(uow, *, clock: AdjustableClock, by: timedelta, actor) -> datetime` | Clock moved, move audited | `ValueError` if `by` ≤ 0 | admin "advance time" (preference), NFR-003.1 | uow, clock |

### identity

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `get_current_user(request: Request) -> CurrentUser` (FastAPI dependency) | User named by the `X-Dev-User` header | `Unauthenticated` (missing or unknown) | NFR-002.2 | `IdentityProvider` from `app.state.container` |
| `require_role(*roles: Role) -> Callable[..., CurrentUser]` | A dependency returning the user if their role is in `roles` | `Forbidden` (raised by the dependency) | NFR-002.2 | `get_current_user` |
| `student_id_of(user: CurrentUser) -> StudentId` | The student's id | `Forbidden` if not a Student | NFR-002.2 | — |

Port `IdentityProvider`: `resolve(user_ref: str) -> CurrentUser | None`, `list_users() -> list[CurrentUser]`. Adapter `SeededIdentityProvider` (three synthetic users: `u-student-1`, `u-officer-1`, `u-admin-1`).

### eligibility (pure, no I/O)

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `assess(inputs: EligibilityInput, thresholds: RuleSetThresholds) -> EligibilityAssessment` | One `RuleResult` (Pass/Fail/Escalate + plain-language reason) per rule, plus `rule_set_version` and the inputs | — (total over valid input) | FR-002.1, FR-002.3, FR-002.6, NFR-003.4 | thresholds (passed in) |
| `EnrollmentRule.evaluate(inputs, thresholds) -> RuleResult` | ≥ 6 Pass, 3–5 Escalate, < 3 Fail (configurable) | — | FR-002.6 | thresholds |
| `SapRule.evaluate(...)` | Meeting Pass, Warning Escalate, Suspended Fail | — | FR-002.6 | — |
| `FundAvailabilityRule.evaluate(...)` | Balance ≥ amount Pass, else Fail; never Escalate | — | FR-002.6 | — |
| `NoOverdueLoansRule.evaluate(...)` | No overdue installment Pass, else Fail | — | FR-002.6, FR-006.3 | — |

`RULES` is the ordered tuple of the four rule instances.

### review

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `open(uow, *, kind, application_id, student_id, term_id, payment_deadline: date, requested_amount, tuition_gap, pending_aid_total, rule_outcomes: tuple[RuleOutcomeView, ...], student_explanation: str \| None, actor, clock) -> ExceptionReview` | OPEN review, audited | `ReviewAlreadyOpen` | FR-002.2 (escalate), FR-002.4 (appeal) | uow, clock |
| `get(uow, *, review_id) -> ExceptionReview` | The review | `ReviewNotFound` | FR-003.1 | uow |
| `list_open(uow) -> list[ExceptionReview]` | All OPEN reviews of both kinds, earliest `payment_deadline` first | — | FR-003.1 | uow |
| `resolve(uow, *, review_id, decision: ReviewDecision, rationale: str, officer_id: UserId, clock) -> ExceptionReview` | Compare-and-set OPEN → RESOLVED | `MissingRationale` (blank), `ReviewNotOpen` (lost the race), `ReviewNotFound` | FR-003.2 | uow, clock |
| `find_expired(uow, *, clock) -> list[ExceptionReview]` | OPEN reviews past their deadline | — | FR-003.5 | uow, clock |
| `expire(uow, *, review_id, actor, clock) -> ExceptionReview` | Compare-and-set OPEN → EXPIRED | `ReviewNotOpen`, `ReviewNotFound` | FR-003.5 | uow, clock |

### ledger

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `available_balance(uow, *, fund_id) -> Money` | Derived from entries | `FundNotFound` | FR-002.6, FR-006.1 | uow |
| `balances(uow, *, fund_id) -> FundBalances` | Initial capital, available, reserved, disbursed principal, repaid principal | `FundNotFound` | FR-006.1, NFR-001.4 | uow |
| `reserve(uow, *, fund_id, application_id, amount, idempotency_key, actor, clock) -> LedgerEntry` | AVAILABLE → RESERVED, audited | `InsufficientFunds`, `IdempotencyKeyReused`, `FundNotFound` | FR-002.5, FR-006.1, NFR-001.1, NFR-001.2 | uow (immediate), clock |
| `release(uow, *, fund_id, application_id, idempotency_key, actor, clock) -> LedgerEntry` | RESERVED → AVAILABLE | `NoActiveReservation`, `IdempotencyKeyReused` | FR-002.5, FR-004.3, NFR-001.2 | uow (immediate), clock |
| `disburse(uow, *, fund_id, application_id, idempotency_key, actor, clock) -> LedgerEntry` | RESERVED → DISBURSED_PRINCIPAL | `NoActiveReservation`, `IdempotencyKeyReused` | FR-002.5, NFR-001.2 | uow (immediate), clock |
| `credit_repayment(uow, *, fund_id, loan_id, payment_id, amount, idempotency_key, actor, clock) -> LedgerEntry` | DISBURSED_PRINCIPAL → AVAILABLE | `IdempotencyKeyReused`, `FundNotFound` | FR-006.2, NFR-001.2 | uow (immediate), clock |
| `verify_invariant(uow, *, fund_id) -> InvariantReport` | `ok` if available = capital − reserved − disbursed + repaid | `FundNotFound` | NFR-001.4 | uow |

`DEFAULT_FUND_ID = "fund-main"`: the prototype has one fund.

### repayment

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `split_installments(principal: Money, count: int) -> tuple[Money, ...]` | Equal parts, remainder cents on the last (pure) | `ValueError` if count < 1 | FR-005.1 | — |
| `create_loan(uow, *, application_id, student_id, term_id, fund_id, principal, actor, clock) -> Loan` | ACTIVE loan + schedule with amounts, no dates | `LoanAlreadyExists` | FR-005.1 | uow, clock, config |
| `set_due_dates(uow, *, loan_id, posted_at: datetime, actor, clock) -> RepaymentSchedule` | First due 30 days after `posted_at`, then monthly | `LoanNotFound`, `DueDatesAlreadySet` | FR-005.1 | uow, clock |
| `get_loan(uow, *, loan_id, student_id: StudentId \| None) -> Loan` | The loan | `LoanNotFound` | NFR-002.2 | uow |
| `list_loans(uow, *, student_id) -> list[Loan]` | Student's loans | — | NFR-002.2 | uow |
| `get_schedule(uow, *, loan_id, student_id) -> RepaymentSchedule` | Schedule (0% interest) | `LoanNotFound` | FR-005.1 | uow |
| `has_active_loan(uow, *, student_id, term_id) -> bool` | Early check for one-per-term | — | FR-001.6 | uow |
| `has_overdue_installment(uow, *, student_id, clock) -> bool` | From due dates + clock, not only the flag | — | FR-002.6, FR-006.3 | uow, clock, config |
| `make_payment(uow, *, loan_id, student_id, amount, method_token, idempotency_key, payments: PaymentsPort, actor, clock) -> Payment` | Charged, applied to installments, credited to the fund; loan REPAID when outstanding hits 0 | `InvalidPaymentAmount`, `AmountExceedsOutstanding`, `PaymentDeclined`, `LoanNotFound`, `LoanNotActive` | FR-005.2, FR-006.2, NFR-001.2, NFR-002.4 | uow (immediate), clock, payments |
| `enroll_autopay(uow, *, loan_id, student_id, method_token, payments, actor, clock) -> AutopayEnrollment` | Mandate recorded | `AutopayAlreadyEnrolled`, `LoanNotFound`, `LoanNotActive` | FR-005.2, NFR-002.4 | uow, clock, payments |
| `send_due_reminders(uow, *, notifier: NotificationsPort, clock) -> list[Installment]` | One reminder per installment, N days before due | — | FR-005.3 | uow, clock, notifier, config |
| `flag_overdue(uow, *, clock) -> list[Loan]` | Installments marked OVERDUE, loans flagged | — | FR-006.3 | uow, clock, config |
| `list_flagged_loans(uow) -> list[Loan]` | Loans flagged for follow-up | — | FR-006.3 | uow |

Ports: `PaymentsPort.charge(*, method_token, amount, idempotency_key) -> ChargeResult`, `PaymentsPort.enroll_autopay(*, method_token, loan_id, schedule) -> str` (adapter `MockPaymentsAdapter`); `NotificationsPort.send(uow, *, student_id, subject, body, idempotency_key) -> str` (adapter `OutboxNotifier`, which also has `list_for(uow, *, student_id) -> list[OutboxMessage]` for the mock inbox).

### disbursement

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `create_pending(uow, *, loan_id, student_id, term_id, amount, actor, clock) -> Disbursement` | PENDING disbursement | `DisbursementAlreadyExists` | FR-004.2 | uow, clock |
| `post_pending(*, uow_factory, sis: SisPostingPort, clock) -> PostingRunResult` | Each PENDING posted with `disbursement_id` as idempotency key; on success `posted_at` set and `repayment.set_due_dates` called; failures stay PENDING | — (`SisUnavailable` per item is caught and retried next run) | NFR-005.3, FR-005.1, NFR-001.2 | uow_factory, clock, sis |
| `get_for_loan(uow, *, loan_id, student_id) -> Disbursement` | The loan's disbursement | `DisbursementNotFound` | FR-004.2, NFR-005.3 | uow |

Port `SisPostingPort.post_disbursement_credit(*, student_id, term_id, amount, idempotency_key) -> SisPostingReceipt`; raises `SisUnavailable`.

### agreements

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `generate(uow, *, application_id, student_id, term_id, fund_id, amount, actor, clock) -> LoanAgreement` | PENDING_SIGNATURE, `sign_by = now + signing window`, installment amounts | — | FR-004.1 | uow, clock, config |
| `get(uow, *, agreement_id, student_id) -> LoanAgreement` | The agreement | `AgreementNotFound` | FR-004.1 | uow |
| `render_for_review(uow, *, agreement_id, student_id, esign: ESignaturePort) -> RenderedDocument` | Unsigned PDF | `AgreementNotFound` | FR-004.1, AC-01 "review and sign" | uow, esign |
| `sign(uow, *, agreement_id, student_id, consent: ConsentInput, esign, clock) -> LoanAgreement` | SIGNED with hash, timestamp, consent; reservation converted, Loan created, Disbursement pending, all in one transaction | `SigningWindowClosed`, `AgreementNotPendingSignature`, `ConsentRequired`, `AgreementNotFound` | FR-004.2, FR-002.5, FR-005.1, NFR-004.1, NFR-004.2, NFR-001.2 | uow (immediate), clock, esign |
| `find_unsigned_past_window(uow, *, clock) -> list[LoanAgreement]` | PENDING_SIGNATURE past `sign_by` | — | FR-004.3 | uow, clock |
| `expire(uow, *, agreement_id, actor, clock) -> LoanAgreement` | Compare-and-set → EXPIRED | `AgreementNotPendingSignature` | FR-004.3 | uow, clock |
| `download_signed(uow, *, agreement_id, student_id) -> RenderedDocument` | Stored signed PDF, unaltered | `AgreementNotFound`, `AgreementNotSigned` | NFR-004.2, NFR-004.3 | uow |

Port `ESignaturePort.render(agreement) -> RenderedDocument`, `ESignaturePort.capture(*, agreement, consent, signed_at) -> SignatureEvidence` (adapter `ClickToSignAdapter`).

### applications

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `calculate_tuition_gap(data: StudentTermData) -> Money` | Balance − accepted, undisbursed aid (pure; may be ≤ 0) | — | FR-001.1 | — |
| `validate_amount(uow, *, requested_amount, tuition_gap) -> AmountValidation` | `ok`, or `message` such as "exceeds your tuition gap of $600" | — (bad amounts are a result) | FR-001.3, AC-01 | uow, config |
| `start(*, uow_factory, sis: SisReaderPort, student_id, term_id) -> ApplicationStart` | Gap, pending aid, min, `max_requestable = min(gap, max)`, deadline. Creates nothing | `TryAgainLater`, `NoTuitionGap`, `ActiveApplicationExists` | FR-001.1, FR-001.2, FR-001.4, FR-001.6, AC-01 | uow_factory, sis, config |
| `submit(*, uow_factory, sis, clock, student_id, term_id, requested_amount, idempotency_key) -> SubmissionResult` | Application + decision; approved → reservation + agreement; escalated → review; denied → reasons | `TryAgainLater`, `NoTuitionGap`, `AmountOutOfRange`, `ActiveApplicationExists` | FR-001.2–001.6, FR-002.1–002.3, FR-002.5, FR-002.6, FR-004.1, FR-006.1, NFR-001.1, NFR-001.2, NFR-003.4, NFR-005.1 | uow_factory (immediate), clock, sis, config |
| `decide(assessment) -> DecisionOutcome` | Fail → DENIED; else Escalate → ESCALATED; else APPROVED (pure) | — | FR-002.2 | — |
| `denial_reasons(assessment) -> tuple[str, ...]` | Reason of every failed rule (pure) | — | FR-002.3 | — |
| `get(uow, *, application_id, student_id: StudentId \| None) -> LoanApplication` | Application with assessment and decisions | `ApplicationNotFound` | NFR-002.2 | uow |
| `list_for_student(uow, *, student_id) -> list[LoanApplication]` | Student's applications | — | NFR-002.2 | uow |
| `appeal(uow, *, application_id, student_id, explanation: str \| None, clock) -> ExceptionReview` | APPEAL review with original outcomes; status UNDER_REVIEW | `ApplicationNotDenied`, `AppealWindowClosed`, `AppealAlreadyUsed`, `ApplicationNotFound` | FR-002.4 | uow (immediate), clock, config |
| `resolve_review(*, uow_factory, sis, clock, review_id, officer_id: UserId, decision: ReviewDecision, rationale: str) -> Decision` | Officer decision recorded and audited; approve → reservation + agreement | `MissingRationale`, `ReviewNotOpen`, `ReviewNotFound`, `PaymentDeadlinePassed`, `TryAgainLater`, `AmountExceedsRecalculatedGap`, `FundCannotCover` | FR-003.2–003.6, FR-006.1 | uow_factory (immediate), clock, sis |
| `expire_overdue_reviews(*, uow_factory, clock) -> list[ApplicationId]` | Reviews expired, applications denied with "Review not completed before the payment deadline." | — | FR-003.5 | uow_factory, clock |
| `expire_unsigned(*, uow_factory, clock) -> list[ApplicationId]` | Agreements expired, applications EXPIRED, reservations released | — | FR-004.3, FR-002.5 | uow_factory, clock |

Port `SisReaderPort.get_student_term_data(*, student_id, term_id) -> StudentTermData`; raises `SisUnavailable` (adapter `HttpSisAdapter`, 3 s timeout).

### jobs

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `build_scheduler(*, uow_factory, clock, sis: SisPostingPort, notifier: NotificationsPort) -> BackgroundScheduler` | Scheduler with the five jobs registered, not started | — | all below | all listed |
| `run_review_expiry(*, uow_factory, clock) -> None` | Calls `applications.expire_overdue_reviews` | Logs and swallows; next run retries | FR-003.5 | uow_factory, clock |
| `run_signing_expiry(*, uow_factory, clock) -> None` | Calls `applications.expire_unsigned` | same | FR-004.3 | uow_factory, clock |
| `run_disbursement_posting(*, uow_factory, sis, clock) -> None` | Calls `disbursement.post_pending` | same | NFR-005.3 | uow_factory, clock, sis |
| `run_due_reminders(*, uow_factory, notifier, clock) -> None` | Calls `repayment.send_due_reminders` | same | FR-005.3 | uow_factory, clock, notifier |
| `run_overdue_flagging(*, uow_factory, clock) -> None` | Calls `repayment.flag_overdue` | same | FR-006.3 | uow_factory, clock |

### web

| Signature | Success result | Fails with | Spec rule | Injected |
|---|---|---|---|---|
| `to_http_error(exc: DomainError) -> tuple[int, dict[str, str]]` | `(status, {"error": code, "message": user text})` | — | FR-001.4, FR-003.6, AC-01 messages | — |
| `not_implemented_handler(request, exc) -> JSONResponse` *(skeleton only, implemented)* | 501 `{"error": "not_implemented", "message": ...}` | — | — | — |
| `get_container(request) -> Container` *(implemented)* | Adapters chosen at startup | — | — | — |

---

## Part 2: REST API

Base URL `http://localhost:8000/api`. Every route currently returns **501** with `{"error": "not_implemented", "message": "<METHOD> <path> maps to <function>, which is not implemented yet."}`.

Authentication (prototype): header `X-Dev-User: u-student-1 | u-officer-1 | u-admin-1`. Money-moving POSTs require an `Idempotency-Key` header. Domain errors will map through `web.to_http_error`: not found → 404, forbidden → 403, validation/rule refusals → 422, state conflicts (lost compare-and-set, active application exists) → 409, `TryAgainLater` → 503.

### Student

| Method & path | Function | Request | Success | Spec rules |
|---|---|---|---|---|
| `GET /terms/{term_id}/application-start` | `applications.start` | — | 200 `ApplicationStart` | FR-001.1, 001.2, 001.4, 001.5, 001.6; AC-01 sc. 1 |
| `POST /applications/validate-amount` | `applications.validate_amount` | `{requested_amount, tuition_gap}` | 200 `AmountValidation` | FR-001.3; AC-01 sc. 5 |
| `POST /applications` | `applications.submit` | `{term_id, requested_amount}` + `Idempotency-Key` | 201 `SubmissionResult` | FR-001.2–001.6, FR-002.1–002.3, 002.5, 002.6, FR-004.1, FR-006.1, NFR-001.1, 001.2, NFR-005.1, 005.2; AC-01 sc. 2–4; AC-02 |
| `GET /applications` | `applications.list_for_student` | — | 200 `LoanApplication[]` | NFR-002.2 |
| `GET /applications/{application_id}` | `applications.get` | — | 200 `LoanApplication` (decision, reasons) | FR-002.3; AC-01 sc. 3 |
| `POST /applications/{application_id}/appeal` | `applications.appeal` | `{explanation?}` | 201 `ExceptionReview` | FR-002.4 |
| `GET /agreements/{agreement_id}` | `agreements.get` | — | 200 `LoanAgreement` | FR-004.1 |
| `GET /agreements/{agreement_id}/document` | `agreements.render_for_review` | — | 200 `application/pdf` | FR-004.1; AC-01 sc. 2 |
| `POST /agreements/{agreement_id}/signature` | `agreements.sign` | `{consent_to_electronic_records, intent_to_sign, typed_name}` | 200 `LoanAgreement` (SIGNED) | FR-004.2, FR-002.5, FR-005.1, NFR-004.1, 004.2, NFR-001.2 |
| `GET /agreements/{agreement_id}/signed-document` | `agreements.download_signed` | — | 200 `application/pdf` attachment | NFR-004.2, 004.3 |
| `GET /loans` | `repayment.list_loans` | — | 200 `Loan[]` | NFR-002.2 |
| `GET /loans/{loan_id}` | `repayment.get_loan` | — | 200 `Loan` | FR-005 |
| `GET /loans/{loan_id}/schedule` | `repayment.get_schedule` | — | 200 `RepaymentSchedule` | FR-005.1 |
| `GET /loans/{loan_id}/disbursement` | `disbursement.get_for_loan` | — | 200 `Disbursement` | FR-004.2, NFR-005.3 |
| `POST /loans/{loan_id}/payments` | `repayment.make_payment` | `{amount, method_token}` + `Idempotency-Key` | 201 `Payment` | FR-005.2, FR-006.2, NFR-001.2, NFR-002.4 |
| `POST /loans/{loan_id}/autopay` | `repayment.enroll_autopay` | `{method_token}` | 201 `AutopayEnrollment` | FR-005.2, NFR-002.4 |
| `GET /notifications` | `OutboxNotifier.list_for` | — | 200 `OutboxMessage[]` (mock inbox) | FR-005.3 |

### Financial Aid Officer

| Method & path | Function | Request | Success | Spec rules |
|---|---|---|---|---|
| `GET /reviews` | `review.list_open` | — | 200 `ExceptionReview[]` by deadline | FR-003.1; AC-02 sc. 1 |
| `GET /reviews/{review_id}` | `review.get` | — | 200 `ExceptionReview` (gap, awards, triggering rules) | FR-003 story, FR-002.4 |
| `POST /reviews/{review_id}/resolution` | `applications.resolve_review` | `{decision: "approve"\|"deny", rationale}` | 200 `Decision` | FR-003.2–003.6, FR-006.1 |
| `GET /officer/loans/flagged` | `repayment.list_flagged_loans` | — | 200 `Loan[]` | FR-006.3 |
| `GET /funds/{fund_id}/balances` *(officer, admin)* | `ledger.balances` | — | 200 `FundBalances` | FR-006.1, FR-006.2 |
| `GET /funds/{fund_id}/invariant` *(officer, admin)* | `ledger.verify_invariant` | — | 200 `InvariantReport` | NFR-001.4 |
| `GET /audit/records?entity_type=&entity_id=` *(officer, admin)* | `audit.records_for` | — | 200 `AuditRecord[]` | FR-003.4, NFR-003.1, 003.2, 003.4 |
| `GET /audit/verify` *(officer, admin)* | `audit.verify_chain` | — | 200 `ChainVerification` | NFR-003.3 |

### Identity, configuration, demo

| Method & path | Function | Request | Success | Spec rules |
|---|---|---|---|---|
| `GET /me` *(any role)* | `identity.get_current_user` | — | 200 `CurrentUser` | NFR-002.2 |
| `GET /dev/users` *(no auth, prototype only)* | `SeededIdentityProvider.list_users` | — | 200 `CurrentUser[]` | NFR-002.2 (user-switcher) |
| `GET /config` *(any role)* | `config.current` | — | 200 `ConfigSnapshot` | FR-001.3, FR-002.6 and the other configurable values |
| `PATCH /config` *(admin)* | `config.update` | `{changes: {ConfigKey: value}}` | 200 `ConfigSnapshot` | FR-002.6, NFR-003.1 |
| `POST /admin/clock/advance` *(admin)* | `config.advance_clock` | `{days, hours}` | 200 new `now` | admin "advance time" (preference) |

### Requirement coverage

Every requirement in spec.md, and where it is reached over REST. Requirements without a route of their own are enforced inside the functions named.

| Requirement | Route(s) | Notes |
|---|---|---|
| FR-001.1 | `GET /terms/{id}/application-start` | |
| FR-001.2 | `GET /terms/{id}/application-start`, `POST /applications` | Two SIS reads |
| FR-001.3 | `POST /applications/validate-amount`, `POST /applications` | |
| FR-001.4 | same as FR-001.2 | 503 "try again later" |
| FR-001.5 | same as FR-001.2 | No route writes SIS data |
| FR-001.6 | `GET /terms/{id}/application-start`, `POST /applications` | Partial unique index enforces it |
| FR-002.1, 002.2, 002.6 | `POST /applications` | Inside `submit` |
| FR-002.3 | `POST /applications`, `GET /applications/{id}` | |
| FR-002.4 | `POST /applications/{id}/appeal` | |
| FR-002.5 | `POST /applications`, `POST /agreements/{id}/signature` | Release on expiry is job-only |
| FR-003.1 | `GET /reviews` | |
| FR-003.2, 003.3, 003.4, 003.6 | `POST /reviews/{id}/resolution` | |
| FR-003.5 | — | Job `run_review_expiry`; result visible at `GET /applications/{id}` |
| FR-004.1 | `POST /applications`, `GET /agreements/{id}`, `GET /agreements/{id}/document` | |
| FR-004.2 | `POST /agreements/{id}/signature`, `GET /loans/{id}/disbursement` | |
| FR-004.3 | — | Job `run_signing_expiry`; `sign` also refuses late |
| FR-005.1 | `POST /agreements/{id}/signature`, `GET /loans/{id}/schedule` | Dates set by the posting job |
| FR-005.2 | `POST /loans/{id}/payments`, `POST /loans/{id}/autopay` | |
| FR-005.3 | `GET /notifications` | Sent by job `run_due_reminders` |
| FR-006.1 | `POST /applications`, `POST /reviews/{id}/resolution`, `GET /funds/{id}/balances` | |
| FR-006.2 | `POST /loans/{id}/payments`, `GET /funds/{id}/balances` | |
| FR-006.3 | `GET /officer/loans/flagged` | Flagged by job `run_overdue_flagging` |
| NFR-001.1 | `POST /applications`, `POST /reviews/{id}/resolution` | `BEGIN IMMEDIATE` |
| NFR-001.2 | `POST /applications`, `POST /agreements/{id}/signature`, `POST /loans/{id}/payments` | `Idempotency-Key` header |
| NFR-001.3 | all money fields | Decimal strings |
| NFR-001.4 | `GET /funds/{id}/invariant` | |
| NFR-002.1 | — | Deferred: storage encryption and TLS at ingress (architecture §5) |
| NFR-002.2 | every route | `require_role` + student scoping |
| NFR-002.3 | — | Deferred to the real identity adapter |
| NFR-002.4 | `POST /loans/{id}/payments`, `POST /loans/{id}/autopay` | Tokens only |
| NFR-002.5 | — | Institutional process; deferred |
| NFR-003.1, 003.2, 003.4 | `GET /audit/records` | |
| NFR-003.3 | `GET /audit/verify` | |
| NFR-004.1, 004.2 | `POST /agreements/{id}/signature` | |
| NFR-004.3 | `GET /agreements/{id}/signed-document` | |
| NFR-004.4 | — | Content approval, not code |
| NFR-005.1, 005.2 | `POST /applications` (and the SIS-reading routes) | |
| NFR-005.3 | `GET /loans/{id}/disbursement` | Posted by job `run_disbursement_posting` |
| NFR-005.4 | — | Not achievable as built (architecture §5) |

---

## Part 3: Mock SIS API (separate container, `http://localhost:8001`)

Every route currently returns 501.

| Method & path | Function | Request | Success |
|---|---|---|---|
| `GET /students/{student_id}/terms/{term_id}` | `mock_sis.get_student_term` | — | 200 balance, aid awards, credits, SAP, hold, payment deadline |
| `POST /disbursement-credits` | `mock_sis.post_disbursement_credit` | `{student_id, term_id, amount}` + `Idempotency-Key` | 200 `{sis_transaction_id, posted_at}`; same key → same response |
| `PUT /toggles` | `mock_sis.set_toggles` | `{outage, latency_ms, incomplete_data}` | 200 current toggles |
