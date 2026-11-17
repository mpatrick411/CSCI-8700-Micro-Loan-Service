# Implementation plan: Tuition Gap Micro-Loan Service

Sources: `spec.md`, `architecture.md`, `contracts.md`, `test_plan.md`, the skeleton under `app/`, and the suite under `tests/` (25 tests).

## Baseline (2026-11-16)

`pytest tests` → **3 failed, 22 errors, 0 passed.** Every test fails during fixture setup: `make_world` calls `container.uow_factory(immediate=True)`, which raises `NotImplementedError: kernel.SqliteUnitOfWorkFactory.__call__`. If it got past that, `ledger.seed_fund` would raise next. No route has been reached yet.

## Conventions used in this plan

- **Criteria IDs.** The spec has two acceptance criteria, each with numbered scenarios: AC-01.1 to AC-01.5 and AC-02.1 to AC-02.3 (test-plan IDs TP-AC01-0n and TP-AC02-0n). Tests with no acceptance criterion show "—" and give their FR instead.
- **Controls may go green early.** A control or inside-boundary test (marked *control*) sits in the same slice as the rejection it pairs with. It may already pass once an earlier slice is done. In its own slice it guards against the rejection logic over-reaching.
- **Partial functions.** Some functions are built across several slices, for example `decide` grows one branch per slice. Each slice lists only the part it adds. A slice should not implement branches that a later slice owns. Otherwise that later slice's tests are green before the slice starts, and a failure no longer points at one cause.
- **Tables.** Each module adds its own `tables.py`. A slice names the tables it introduces. Only the owning module reads or writes them. `SqliteUnitOfWorkFactory` creates the schema from all of them (DQ-1).
- **Done when** is the same for every slice: the listed tests pass, and no test that passed before fails. Slice 3 (Demo wiring) has no tests and its own manual check.

---

## Slice 1: Walking skeleton (see my tuition gap)

- **Goal:** A logged-in student calls application-start and gets the tuition gap and maximum requestable amount, computed from SIS data, through the full identity → route → service → SIS port → config → JSON flow.
- **Spec sources:** FR-001.1 (gap formula), FR-001.2 (SIS read at start), FR-001.3 (show gap and max requestable), FR-001.5, FR-001.6 (start creates nothing), NFR-001.3, NFR-002.2; architecture §3 steps 1, 3, 4.
- **Criteria:** AC-01.1
- **Tests that should turn green:**
  - `test_TP_AC01_01`
  - `test_TP_GAP_01` *(control for `test_TP_GAP_02`)*
- **Skeleton to fill in:**
  - `kernel.Money`: `of`, `from_cents`, `to_cents`, `zero`, `+`, `-`, `<`, `<=`, `>`, `>=`, `is_positive`
  - `kernel.SqlAlchemyUnitOfWork`: `session`, `__enter__`, `__exit__`, `commit`, `rollback`; `kernel.SqliteUnitOfWorkFactory.__call__` (`immediate=True` → `BEGIN IMMEDIATE`)
  - Schema creation (DQ-1): on its first call for a database, `SqliteUnitOfWorkFactory` creates every module's `tables.py` metadata, the audit UPDATE/DELETE triggers and the partial unique index on active applications/loans, and does nothing if the schema already exists. `build_container` stays free of I/O.
  - `audit.append` (hash chain), with `audit/tables.py`. Needed because the fixture's `seed_fund` is audited.
  - `ledger.seed_fund`, with `ledger/tables.py` (entries with a unique idempotency key)
  - `identity.get_current_user`, `identity.require_role`, `identity.student_id_of`; `SeededIdentityProvider.resolve`
  - `config.current` (defaults when no version is stored), with `config/tables.py`
  - `applications.calculate_tuition_gap`; `applications.start` (SIS read, gap, `min_amount`, `max_requestable`, deadline only; the refusals come in slices 2 and 12); `applications.list_for_student`, with `applications/tables.py`
  - `web.to_jsonable` (DQ-2): Money as a 2-dp decimal string, datetimes as ISO 8601 with offset. The routes in this slice return their result through it.
  - DomainError handler (DQ-3): `create_app` registers `web.domain_error_handler`, which calls `to_http_error`. `to_http_error` itself is filled in slice 2.
  - Routes: `GET /terms/{term_id}/application-start`, `GET /applications`
- **Depends on:** —
- **Status:** not started
- **Design decisions:** DQ-1 (schema creation), DQ-2 (Money as a JSON decimal string), DQ-3 (handler registration), all resolved below.
- **Watch for:** FastAPI's own encoder runs before any response class and turns `Money` into `{"amount": 600.0}`. A route must return `JSONResponse(to_jsonable(result), status_code=...)` itself, and must pass the status code explicitly, because a returned Response ignores the decorator's `status_code`.

## Slice 2: Start refusals and the NC harness

- **Goal:** Starting an application is refused with a mapped HTTP error when the SIS is unavailable (503, "try again later") or the gap is below the minimum loan amount (422). The read endpoints that the "nothing created" check uses all work.
- **Spec sources:** FR-001.1 (gap < minimum), FR-001.4, NFR-005.2 (handled as FR-001.4); contracts Part 2 error mapping; test_plan §0.2 NC.
- **Criteria:** — (FR-001.4 and the FR-001.1 minimum clause have no AC)
- **Tests that should turn green:**
  - `test_TP_SIS_01`
  - `test_TP_GAP_02`
- **Skeleton to fill in:**
  - `web.to_http_error` (status per contracts Part 2, including `Unauthenticated` → 401 (DQ-3) and `InvalidMoney` → 422 `invalid_money` (DQ-7); body `{"error": code, "message": text}` with a non-empty message)
  - `applications.start`: map `SisUnavailable` → `TryAgainLater`; raise `NoTuitionGap` when gap < configured minimum
  - `repayment.list_loans`, with `repayment/tables.py` (returns `[]` for now). The loans side of the DQ-1 partial unique index (one active loan per student and term, FR-001.6) is added with this table: slice 1 created only the applications side, because the loans table did not exist yet.
  - `review.list_open`, with `review/tables.py` (returns OPEN reviews; the sort order is untested, see "Leftovers")
  - `ledger.balances`
  - Routes: `GET /loans`, `GET /reviews`, `GET /funds/{fund_id}/balances`
- **Depends on:** 1
- **Status:** not started
- **Design decisions:** DQ-3 (uses the handler registered in slice 1), DQ-7

## Slice 3: Demo wiring

- **Goal:** The app runs against the real mock SIS container and the real clock, and the demo fund is seeded, so slice 1 can be shown through `/docs`.
- **Spec sources:** FR-001.2, FR-001.4 (adapter turns failures into `SisUnavailable`), FR-001.5, NFR-005.2 (3 s timeout); architecture §2 "Ports and prototype adapters" and "Mock SIS service"; DQ-5, DQ-6.
- **Criteria:** —
- **Tests that should turn green:** none (no test uses the real SIS, clock or startup seed)
- **Skeleton to fill in:**
  - `mock_sis.get_student_term` (honours the toggles), `mock_sis.set_student_term`, `mock_sis.set_toggles`
  - `HttpSisAdapter.get_student_term_data` (3 s timeout; timeout, transport error, incomplete data or unknown SAP status → `SisUnavailable`)
  - The real clock in the container: `AdjustableClock.now`, `AdjustableClock.today`
  - DQ-5 startup seed: the lifespan seeds `fund-main` with $10,000.00 only when `SEED_DEFAULT_FUND=1`; `docker-compose.yml` sets `SEED_DEFAULT_FUND: "1"` on the app service
  - Routes: mock SIS `GET /students/{student_id}/terms/{term_id}`, `PUT /students/{student_id}/terms/{term_id}`, `PUT /toggles`
- **Depends on:** 1
- **Done when:** with the app and the mock SIS running, a manual check in `/docs` shows a PUT of S1001's SIS data, then GET application-start returning gap `"600.00"`; and the full test suite shows no newly failing test.
- **Status:** not started
- **Design decisions:** DQ-8 (institution time zone), DQ-9 (incomplete data shape), DQ-10 (mock SIS status codes), resolved below.
- **Watch for:** `AdjustableClock.today()` needs the institution's time zone, which the spec does not give (test_plan G-17). The test fixture uses America/Chicago (DQ-8).

## Slice 4: Automatic approval (submit → assess → reserve → agreement)

- **Goal:** A fully eligible student submits $600.00. The application is stored with its assessment and rule-set version, approved automatically, $600.00 is reserved from the fund, and a pending-signature agreement can be fetched and rendered as a PDF.
- **Spec sources:** FR-001.2 (re-read at submit), FR-002.1, FR-002.2 (approve branch), FR-002.5 (reserve), FR-002.6 (rule set evaluated, version recorded), FR-004.1, FR-006.1, NFR-001.1, NFR-003.1, NFR-003.2, NFR-003.4; architecture §3 steps 6–13.
- **Criteria:** AC-01.2
- **Tests that should turn green:**
  - `test_TP_AC01_02`
- **Skeleton to fill in:**
  - `applications.submit`, approve path: SIS re-read before the transaction; one immediate transaction that inserts the application, builds `EligibilityInput`, runs `assess`, stores the assessment with its input snapshot, decides, reserves, generates the agreement and audits
  - `applications.decide` (APPROVED branch only); `applications.get`
  - `eligibility.assess`; the Pass band of `EnrollmentRule`, `SapRule`, `FundAvailabilityRule` and `NoOverdueLoansRule` (the test requires four results, one per rule, in `RULES` order)
  - `config.rule_set`
  - `ledger.available_balance`, `ledger.reserve`
  - `repayment.has_overdue_installment` (no loans exist yet, so it returns False; the overdue arithmetic is untested, see "Leftovers"); `repayment.split_installments` (for the agreement's installment amounts)
  - `agreements.generate`, `agreements.get`, `agreements.render_for_review`, with `agreements/tables.py`; `ClickToSignAdapter.render`
  - Routes: `POST /applications`, `GET /applications/{application_id}`, `GET /agreements/{agreement_id}`, `GET /agreements/{agreement_id}/document`, `GET /config`
- **Depends on:** 2
- **Status:** not started
- **Watch for:** `decision.decided_at` must serialize with its UTC offset. The test compares it with the tz-aware `clock.now()`, and a naive datetime read back from SQLite compares unequal.

## Slice 5: Requested-amount validation

- **Goal:** Requested amounts are checked against the gap, the configured minimum and the configured maximum, by the validate endpoint (`ok`/`message`) and again by submit (422 `application_amount_out_of_range`, nothing created). An amount above the gap gets the "exceeds your tuition gap of $600" message.
- **Spec sources:** FR-001.3; architecture §3 steps 5–6.
- **Criteria:** AC-01.5
- **Tests that should turn green:**
  - `test_TP_AC01_05`
  - `test_TP_AMT_01` *(control)*, `test_TP_AMT_02`
  - `test_TP_AMT_03` *(control)*, `test_TP_AMT_04`
  - `test_TP_AMT_05` *(control)*, `test_TP_AMT_06`
- **Skeleton to fill in:**
  - `applications.validate_amount` (≤ gap, ≥ min, ≤ max; message names the gap)
  - `applications.submit`: raise `AmountOutOfRange` on the recalculated gap before any write
  - Route: `POST /applications/validate-amount`
- **Depends on:** 4
- **Status:** not started
- **Watch for:** All three bounds are inclusive. Compare as `Money` values, never as floats.

## Slice 6: Automatic denial for one failed rule

- **Goal:** A student with 2 credits is denied automatically. The decision and the stored application carry the Enrollment rule's plain-language reason, and no money moves (NM).
- **Spec sources:** FR-002.2 (deny branch), FR-002.3, FR-002.6 (Enrollment Fail band).
- **Criteria:** AC-01.3
- **Tests that should turn green:**
  - `test_TP_AC01_03`
- **Skeleton to fill in:**
  - `applications.decide` (DENIED branch); `applications.denial_reasons`
  - `applications.submit`, deny path: store the decision and reasons; no reservation, agreement or review
  - `EnrollmentRule.evaluate`: Fail band (< `enrollment_escalate_min_credits`)
- **Depends on:** 5
- **Status:** not started

## Slice 7: Denial lists every failed rule

- **Goal:** When more than one rule fails, the denial lists the reason of every failed rule, in `RULES` order, each a plain-language sentence.
- **Spec sources:** FR-002.3; FR-002.6 (SAP "Suspended" → Fail).
- **Criteria:** AC-02.3
- **Tests that should turn green:**
  - `test_TP_AC02_03`
- **Skeleton to fill in:**
  - `SapRule.evaluate`: Fail band (Suspended)
  - `applications.denial_reasons`: every Fail, in rule order (no short-circuit after the first)
- **Depends on:** 6
- **Status:** not started

## Slice 8: Fund availability at the boundary

- **Goal:** The fund rule passes when the available balance exactly covers the request, fails one cent below it, and a Fund-availability denial moves no money.
- **Spec sources:** FR-002.6 (Fund availability), FR-006.1, NFR-001.1, NFR-001.4.
- **Criteria:** —
- **Tests that should turn green:**
  - `test_TP_RUL_05` *(control)*
  - `test_TP_RUL_06`
- **Skeleton to fill in:**
  - `FundAvailabilityRule.evaluate`: Fail band (`available < requested`), never Escalate
  - `ledger.reserve`: raise `InsufficientFunds` when the balance read in the same immediate transaction does not cover the amount (NFR-001.1 safety net)
- **Depends on:** 6
- **Status:** not started
- **Watch for:** Use `>=`, not `>`. Available must exclude active reservations, per NFR-001.4.

## Slice 9: Escalation to an officer review

- **Goal:** When at least one rule escalates and none fails, the application becomes `under_review` and an escalation ExceptionReview opens. The officer dashboard shows the gap, the aid awards and only the rules that returned Escalate or Fail. No money moves.
- **Spec sources:** FR-002.2 (escalate branch), FR-002.6 (SAP Warning, Enrollment 3–5), FR-003.1 (entry content).
- **Criteria:** AC-01.4, AC-02.1
- **Tests that should turn green:**
  - `test_TP_AC01_04`
  - `test_TP_AC02_01`
- **Skeleton to fill in:**
  - `applications.decide` (ESCALATED branch); `applications.submit`, escalate path (`review.open` with the submission snapshot and all four rule outcomes; set `review_id`; status `under_review`)
  - `review.open` (stores all four outcomes); `review.list_open` (entry carries `tuition_gap` and `aid_awards`; outcomes filtered to Escalate and Fail on read)
  - `SapRule.evaluate`: Escalate band (Warning); `EnrollmentRule.evaluate`: Escalate band
- **Depends on:** 7, 8
- **Status:** not started
- **Design decisions:** DQ-4 (the outcome filter lives in `review` reads)

## Slice 10: Enrollment band boundaries

- **Goal:** The Enrollment rule uses the configured thresholds with inclusive lower bounds: 6 credits pass, 5 and 3 escalate.
- **Spec sources:** FR-002.6 (Enrollment), FR-002.6 (thresholds come from the versioned rule set).
- **Criteria:** —
- **Tests that should turn green:**
  - `test_TP_RUL_01` *(control)*
  - `test_TP_RUL_02`
  - `test_TP_RUL_03`
- **Skeleton to fill in:**
  - `EnrollmentRule.evaluate`: read both thresholds from `RuleSetThresholds`, with no hard-coded 6 or 3; `credits >= pass_min` → Pass, `credits >= escalate_min` → Escalate
- **Depends on:** 9
- **Status:** not started

## Slice 11: Fail takes priority over Escalate

- **Goal:** If any rule fails, the application is denied even when another rule escalates. The reasons list only the failed rules, and no review opens.
- **Spec sources:** FR-002.2 (precedence), FR-002.3.
- **Criteria:** AC-02.2
- **Tests that should turn green:**
  - `test_TP_AC02_02` (SAP Fail + Enrollment Escalate)
  - `test_TP_RUL_08` (Fund Fail + Enrollment Escalate)
- **Skeleton to fill in:**
  - `applications.decide`: check Fail before Escalate
  - `applications.denial_reasons`: exclude Escalate outcomes
- **Depends on:** 8, 10
- **Status:** not started

## Slice 12: One active application per student per term

- **Goal:** A second Fall 2026 submission is refused with 409 `application_active_exists` while the first is under review, and is accepted when the first was denied.
- **Spec sources:** FR-001.6; architecture §2 "Concurrency" (partial unique index), §3 step 2.
- **Criteria:** —
- **Tests that should turn green:**
  - `test_TP_ONE_06` *(control)*
  - `test_TP_ONE_04`
- **Skeleton to fill in:**
  - `applications/tables.py`: partial unique index on (student, term) where status ∈ {under_review, approved}, created with the schema (DQ-1); `submit` translates the violation into `ActiveApplicationExists`
  - `applications.start` and `applications.submit`: early active check, which also asks `repayment.has_active_loan`
  - `repayment.has_active_loan`
- **Depends on:** 6, 9
- **Status:** not started

---

## Coverage check

| Criterion | Slice |
|---|---|
| AC-01.1 | 1 |
| AC-01.2 | 4 |
| AC-01.3 | 6 |
| AC-01.4 | 9 |
| AC-01.5 | 5 |
| AC-02.1 | 9 |
| AC-02.2 | 11 |
| AC-02.3 | 7 |

All 25 failing tests are assigned exactly once: 2 + 2 + 0 + 1 + 7 + 1 + 1 + 2 + 2 + 3 + 2 + 2 = 25.

## Leftovers

**Criteria with no slice:** none.
**Failing tests with no slice:** none.

**Contract behaviour inside a slice's functions that no current test checks** (implement it to the contract, but nothing will catch a mistake):
- `submit` idempotency replay (NFR-001.2), and the `TryAgainLater` and `NoTuitionGap` errors at submit
- `review.list_open` sort order (FR-003.1, TP-OFF-01)
- `repayment.has_overdue_installment` arithmetic (TP-RUL-09 to 11)
- AuditRecord contents (TP-AUD-01) and the audit UPDATE/DELETE triggers (NFR-003.3)
- Everything in slice 3 (checked by hand only)

**Functions no slice fills:**
- kernel: `SystemClock.now`, `SystemClock.today`, `AdjustableClock.advance`
- audit: `records_for`, `verify_chain`
- config: `update`, `advance_clock`
- identity adapter: `SeededIdentityProvider.list_users`
- review: `get`, `resolve`, `find_expired`, `expire`
- ledger: `release`, `disburse`, `credit_repayment`, `verify_invariant`
- repayment: `create_loan`, `set_due_dates`, `get_loan`, `get_schedule`, `make_payment`, `enroll_autopay`, `send_due_reminders`, `flag_overdue`, `list_flagged_loans`
- disbursement: `create_pending`, `post_pending`, `get_for_loan`
- agreements: `sign`, `find_unsigned_past_window`, `expire`, `download_signed`; `ClickToSignAdapter.capture`
- applications: `appeal`, `resolve_review`, `expire_overdue_reviews`, `expire_unsigned`
- jobs: `build_scheduler`, `run_review_expiry`, `run_signing_expiry`, `run_disbursement_posting`, `run_due_reminders`, `run_overdue_flagging`
- adapters: `HttpSisAdapter.post_disbursement_credit`, `MockPaymentsAdapter.charge`, `MockPaymentsAdapter.enroll_autopay`, `OutboxNotifier.send`, `OutboxNotifier.list_for`
- mock SIS: `post_disbursement_credit`

**Routes no slice fills** (they keep returning 501):
- `GET /me` will work once slice 1's identity is done; no test covers it.
- `GET /dev/users`, `PATCH /config`, `POST /admin/clock/advance`
- `POST /applications/{application_id}/appeal`
- `POST /agreements/{agreement_id}/signature`, `GET /agreements/{agreement_id}/signed-document`
- `GET /loans/{loan_id}`, `GET /loans/{loan_id}/schedule`, `GET /loans/{loan_id}/disbursement`, `POST /loans/{loan_id}/payments`, `POST /loans/{loan_id}/autopay`, `GET /notifications`
- `GET /reviews/{review_id}`, `POST /reviews/{review_id}/resolution`, `GET /officer/loans/flagged`
- `GET /funds/{fund_id}/invariant`, `GET /audit/records`, `GET /audit/verify`
- Mock SIS `POST /disbursement-credits`

Test-plan rows with no test in the suite yet include SIS-02 to 08, ONE-01 to 03 and 05 to 11, the rest of RUL, and all of VER, APL, OFF, AGR, DIS, SCH, PAY, REM, OVD, LED, AUD, SEC and PERF. The slices above cover only the 25 tests that exist.

## Design questions

- **DQ-1. Who creates the schema?** No skeleton function creates tables, the audit triggers or the partial unique index. `build_container` is documented as "no I/O", and the fixture opens a unit of work right after the app's lifespan starts. Something must create the schema between those two points. Recommendation: one schema step in `create_app`'s lifespan that runs each module's `tables.py` metadata. That is a new function, so it needs your approval.
  - **Resolved:** `SqliteUnitOfWorkFactory` creates the schema the first time it is called for a database. It runs every module's `tables.py` metadata, the audit UPDATE/DELETE triggers and the partial unique index on active applications/loans, and does nothing if the schema already exists. Each module may add a `tables.py` holding only its own tables. `build_container` stays free of I/O. Recorded in the kernel row of contracts.md; built in slice 1.
- **DQ-2. Money in JSON.** `Money` is a dataclass `{amount: Decimal}`. Routes return domain dataclasses with no response model, so FastAPI's `jsonable_encoder` would emit `{"amount": 600.0}`. The tests (`money()` in conftest) and the contracts require `"600.00"`. Recommendation: a `web`-level JSON encoder or response class that renders `Money` as a 2-dp string and datetimes with their offset. It is not in contracts.md.
  - **Resolved:** approved. `web` renders Money as a 2-dp decimal string (e.g. `"600.00"`) and datetimes as ISO 8601 with offset. It does this with a web-level encoder, `web.to_jsonable`, which implements the existing "Money" convention. A response class alone is not enough, because FastAPI's encoder runs first; routes return `JSONResponse(to_jsonable(result), status_code=...)`. Added to the web table of contracts.md; built in slice 1.
- **DQ-3. DomainError → HTTP handler.** `web.to_http_error` exists, but `create_app` registers only the `NotImplementedError` handler, so a `DomainError` becomes a 500. Registering a handler that calls `to_http_error` is a new function. Also, contracts.md gives no status for `Unauthenticated`; 401 is the obvious choice.
  - **Resolved:** approved. `create_app` registers a DomainError handler (`web.domain_error_handler`) that calls `to_http_error`. `Unauthenticated` maps to 401. Both are added to contracts.md. The handler is registered in slice 1; `to_http_error` is filled in slice 2.
- **DQ-4. Where are the Escalate/Fail outcomes filtered?** `review.open` takes `rule_outcomes`. `list_open` must show only Escalate/Fail, while TP-OFF-07 later expects all four outcomes in the officer's AuditRecord. Recommendation: `applications` passes all four, and `review.list_open`/`review.get` filter on read.
  - **Resolved:** recommendation accepted. `applications` passes all four outcomes to `review.open`, and `review.list_open` and `review.get` filter to Escalate and Fail on read. The review rows in contracts.md are updated; built in slice 9.
- **DQ-5. Startup seeding of `fund-main` conflicts with the fixture.** contracts.md says `seed_fund` is "called at startup for fund-main". The fixture seeds the same fund (`ledger.DEFAULT_FUND_ID`) with key `seed-F1` and capitals such as $600.00 or $599.99. If the lifespan seeds first with a different key or capital, the fixture gets `FundAlreadySeeded`. Startup seeding has to be off in tests, for example behind an env var that the tests don't set. Where that switch lives is not specified.
  - **Resolved:** off by default. When the env var `SEED_DEFAULT_FUND=1` is set, startup seeds `fund-main` with $10,000.00. Only `docker-compose.yml` sets it, for the demo; tests never do. The `seed_fund` row in contracts.md is updated; built in slice 3.
- **DQ-6. The /docs demo needs pieces no slice builds.** No test exercises `HttpSisAdapter`, the mock SIS routes, `AdjustableClock`/`SystemClock` or startup fund seeding: tests swap in `FakeSis` and `FrozenClock`. Without them, `/docs` can't run even slice 1. Recommendation: add a "demo wiring" slice right after slice 1, with a manual done-when (start the app and the mock SIS, call application-start from `/docs`). Do you want it?
  - **Resolved:** yes. Added as slice 3 (Demo wiring), after slices 1 and 2; the later slices are renumbered 4–12. It depends on slice 1. Done when: with the app and mock SIS running, a manual check in `/docs` shows a PUT of S1001's SIS data, then GET application-start returning gap `"600.00"`, and the full test suite still shows no newly failing test.
- **DQ-7. More than two decimal places at the route.** Routes call `Money.of(...)` before the service, so `"599.995"` raises `InvalidMoney` (code `invalid_money`). It never reaches `validate_amount`, which per the contracts "never raises for a bad amount". No current test covers this (TP-AMT-08 is not written yet), but the mapping needs a decision before it is.
  - **Resolved:** `InvalidMoney` maps to 422 with code `invalid_money` at the route. Recorded in contracts.md (the `Money.of` row, `to_http_error` and the Part 2 error mapping), so TP-AMT-08 can expect 422 `invalid_money` when it is written. Filled in `to_http_error` in slice 2.
- **DQ-8. Institution time zone for `AdjustableClock.today()`.** The spec never names the institution's time zone (test_plan G-17), but `today()` must return the institution-local date.
  - **Resolved:** a kernel constant `INSTITUTION_TZ = ZoneInfo("America/Chicago")` in `kernel/clock.py`, the same zone as the test fixture. No new option or dependency. Built in slice 3.
- **DQ-9. What does the mock SIS `incomplete_data` toggle leave out?** contracts.md does not say.
  - **Resolved:** when `incomplete_data` is on, the mock SIS returns the normal record with `payment_deadline` omitted. `HttpSisAdapter` treats any missing required field as incomplete data and raises `SisUnavailable`. Built in slice 3.
- **DQ-10. Mock SIS status codes for a missing record and an outage.** contracts.md does not say.
  - **Resolved:** `GET` for a student/term with no stored record returns 404; any `GET` while `outage` is on returns 503. `HttpSisAdapter` treats any non-200 as `SisUnavailable`, so the app answers 503 `sis_try_again_later` in both cases. Built in slice 3.

## Test issues

No test in the suite contradicts the spec. These are weaknesses or traps for tests not yet written:

- **T-1.** `FakeSis.get_student_term_data` builds `SapStatus(r["sap_status"])`, so an unrecognised SAP value raises `ValueError` inside the fake instead of `SisUnavailable`. TP-SIS-03, when written, would get a 500, not a 503. That makes the fake contradict the port contract (FR-001.4).
- **T-2.** `FakeSis.post_disbursement_credit` stamps `posted_at` with `datetime.now(timezone.utc)` (system time) rather than the frozen clock. TP-DIS-01 expects `posted_at` = 2026-09-02 10:00:00, so either `disbursement.post_pending` must use `clock.now()` and ignore the receipt time, or the fake must change.
- **T-3.** The NC check (`World.snapshot`) is weaker than test_plan §0.2. It doesn't look for EligibilityAssessments, LoanAgreements, ledger entries or AuditRecords. A rejected submit that leaves a stray agreement or ledger entry with balanced totals would still pass.
- **T-4.** The AC-01.5 message check is the substring `"exceeds your tuition gap of $600"`. It accepts `$600` and `$600.00`, but it would also accept a wrong gap such as `$6000.00`. That's harmless with these fixtures.
- **Environment, not a test.** The project `.venv` runs Python 3.11.5; architecture.md requires 3.12. `pytest` is not in `requirements.txt`. I installed it, with the requirements, into `.venv` to run the suite.

## Next action

Slice 1 (Walking skeleton): make `test_TP_AC01_01` pass.

## Review notes

- **Application idempotency keys must be unique per student, not globally** (for the submit slice, slice 4). Slice 1's `applications/tables.py` declares `idempotency_key` globally unique. Slice 4 must change that to a uniqueness on (`student_id`, `idempotency_key`), so one student's key can never collide with, or replay, another student's submission.
- **`seed_fund` audit records have `rule_set_version` None**, because `ledger` cannot depend on `config` (architecture.md §2). This is intentional, not a missing value. TP-AUD checks that expect a rule version on every record must allow None for the fund seed.
- **`review.list_open` does not filter to Escalate/Fail yet** (from slice 2). It returns every stored rule outcome. Slice 9 adds the filter on read (DQ-4). No review can exist before slice 9, so nothing visible changes until then.
- **`Loan.outstanding` is stored as a column** (`outstanding_cents` in `repayment/tables.py`, from slice 2). The repayment slices should decide whether to keep it stored or derive it from the installments.
