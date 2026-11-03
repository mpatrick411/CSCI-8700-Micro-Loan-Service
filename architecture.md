# Architecture: Tuition Gap Micro-Loan Service

## 1. Overview

A prototype of the tuition micro-loan service in spec.md. It covers application, automated eligibility decision, officer review, e-signed agreement, disbursement to the SIS tuition balance, and repayment back to the loan fund. The system is a modular monolith: one FastAPI app with server-rendered Jinja + HTMX pages, organised as hexagonal modules over one SQLite database. Every external system (SIS, payments, e-signature, notifications, identity) sits behind a port, and the prototype uses mock adapters for each.

## 2. Modules

Each module has one responsibility. Modules talk to each other only through their public service functions, never through each other's tables. Dependencies run one way only, and there are no cycles.

| Module | Responsibility | May depend on | Required by |
|---|---|---|---|
| `kernel` | Shared primitives that carry no business rules: `Money` (Decimal in domain, integer cents in storage), the injectable `Clock`, and the unit-of-work transaction boundary | — | NFR-001.3; every time-based FR (FR-002.4, FR-003.5, FR-004.3, FR-005.1, FR-005.3, FR-006.3) |
| `audit` | Append hash-chained AuditRecords and verify the chain | kernel | FR-003.4, NFR-003.1–003.4 |
| `config` | Hold versioned configurable values (loan min/max, appeal and signing windows, installment count, reminder and overdue days, eligibility thresholds) and audit every change | kernel, audit | FR-001.3, FR-002.4, FR-002.6, FR-004.3, FR-005.1, FR-005.3, FR-006.3, NFR-003.1 |
| `identity` | Resolve the current user and enforce the role an endpoint declares | kernel | NFR-002.2 (NFR-002.3 later) |
| `eligibility` | Evaluate the rule set against an input snapshot and return an EligibilityAssessment (per-rule Pass/Fail/Escalate, plain-language reasons, rule-set version). Pure: does no I/O | kernel, config | FR-002.1, FR-002.3, FR-002.6 |
| `review` | Keep ExceptionReview cases: open, list for the dashboard, resolve with a mandatory rationale, find expired ones | kernel, audit | FR-002.4, FR-003.1, FR-003.2, FR-003.5 |
| `ledger` | Keep the double-entry ledger for each LoanFund (reserve, release, disburse, credit repayment) and derive balances | kernel, audit | FR-002.5, FR-006.1, FR-006.2, NFR-001.1–001.4 |
| `repayment` | Manage each Loan from signing to full repayment: schedule, payments, reminders, overdue status | kernel, audit, config, ledger, payments port, notifications port | FR-005.1–005.3, FR-006.2, FR-006.3 |
| `disbursement` | Post each Disbursement to the SIS tuition balance and record when it posted | kernel, audit, repayment, SIS port | FR-004.2, FR-005.1 (due dates set at posting), NFR-005.3 |
| `agreements` | Generate the LoanAgreement, capture the e-signature, store the signed document and its hash, and serve downloads | kernel, audit, config, ledger, repayment, disbursement, e-signature port | FR-004.1, FR-004.2, FR-002.5 (convert reservation at signing), NFR-004.1–004.3 |
| `applications` | Own the LoanApplication lifecycle: tuition gap, amount validation, one-active-per-term, applying decisions (automatic or officer), appeals, expiry | kernel, audit, config, eligibility, review, ledger, repayment, agreements, SIS port | FR-001.1–001.6, FR-002.2, FR-002.4, FR-002.5, FR-003.3, FR-003.5, FR-003.6, FR-004.3 |
| `web` | HTTP routes, Jinja/HTMX pages, mapping domain errors to user messages | identity and every domain module's public services | user-facing parts of FR-001–FR-005; FR-003.1 dashboard |
| `jobs` | Run time-based operations on a schedule (APScheduler, in-process) | kernel, applications, disbursement, repayment | FR-003.5, FR-004.3, FR-005.3, FR-006.3, NFR-005.3 |

**Ports and prototype adapters.** Each port is an interface owned by the module that uses it. The adapter is chosen at app startup.

| Port | Used by | Prototype adapter | Required by |
|---|---|---|---|
| SIS (read student term data; post disbursement credit) | applications, disbursement | HTTP client to the mock SIS container, 3 s timeout | FR-001.2, FR-001.4, FR-001.5, FR-003.6, NFR-005.2, NFR-005.3 |
| Payments (one-time charge, autopay enrolment, tokenised method) | repayment | In-process mock that returns token IDs only | FR-005.2, NFR-002.4 |
| E-signature (consent, intent, signed PDF, hash) | agreements | In-process click-to-sign that renders a PDF and records a SHA-256 hash | FR-004.2, NFR-004.1, NFR-004.2 |
| Notifications | repayment | Outbox table, shown on a mock inbox page | FR-005.3 |
| Identity | identity | Seeded users chosen by dev header or UI user-switcher | NFR-002.2 |

**Mock SIS service** (separate container, outside the app). It serves synthetic balances, aid awards, credits, SAP status, holds and deadlines, and accepts disbursement postings deduplicated by idempotency key. Toggles simulate outage, latency and incomplete data.

### Where the cross-cutting decisions are enforced

- **Time.** Every "now" comes from `kernel.Clock`; no module reads system time. Deadlines are checked both by `jobs` and at the moment of action, so a late or skipped job cannot let an expired action through:
  - `agreements.sign` refuses after the signing window (FR-004.3).
  - `applications.appeal` refuses after the appeal window (FR-002.4).
  - Officer approval refuses after the term payment deadline (FR-003.5).
  - The "No overdue loans" input is computed from due dates and `Clock` at assessment time, not only from the job's flag (FR-006.3).
- **Identity.** The `identity.get_current_user()` FastAPI dependency plus `require_role(...)` on each route. Student-facing service functions take `student_id` from the resolved user, never from request parameters. `audit.append` requires an actor (a user ID or `system`).
- **Concurrency.**
  - Decision and reservation run in one `BEGIN IMMEDIATE` transaction (NFR-001.1).
  - A partial unique index on active LoanApplications/Loans per (student, term) enforces FR-001.6.
  - Compare-and-set status updates (`UPDATE … WHERE status = 'pending_signature'`) mean a simultaneous sign and expire cannot both win.
  - Unique idempotency keys on ledger entries, payment credits and SIS postings satisfy NFR-001.2.
- **Errors.** The SIS adapter turns timeout, transport error and incomplete payloads into one `SisUnavailable` error. `applications` maps it to "try again later" at start and submit (FR-001.4) and at officer approval (FR-003.6). Disbursement posting failures stay pending, and `jobs` retries them with the same idempotency key.

## 3. Request flow: student submits an application and is automatically approved

This follows FR-001, FR-002 and AC-01 "Eligible student is automatically approved", then continues through FR-004 and FR-005.1 to show where money moves.

1. The student opens the apply page. `identity` resolves the seeded Student; the route requires the Student role.
2. `applications.start` checks that the student has no active application or loan for the term (FR-001.6), giving early feedback; the database constraint is the actual enforcement.
3. `applications.start` calls the SIS port with a 3 s timeout (FR-001.2, NFR-005.2). On `SisUnavailable` the student sees "try again later" and stops (FR-001.4).
4. `applications` calculates the tuition gap (FR-001.1). It shows the gap ($600) and the maximum requestable amount, which is the smaller of the gap and the configured maximum ($600) (AC-01, first scenario). If the gap is ≤ 0, the student cannot continue. No LoanApplication exists yet (FR-001.6).
5. As the student types an amount, HTMX validates it against the gap and the configured min/max (FR-001.3). $900 shows the "exceeds your tuition gap of $600" message and disables submit (AC-01, last scenario).
6. On submit, `applications` calls the SIS again (FR-001.2), recalculates the gap and revalidates the amount. Any failure stops here as in step 3. All network calls happen before step 7, so no write lock is held during I/O.
7. `applications` opens one `BEGIN IMMEDIATE` transaction and inserts the LoanApplication. The unique index rejects a second active application.
8. Inside the same transaction, `applications` builds the eligibility input snapshot:
   - SIS data from step 6
   - `ledger.available_balance(fund)`
   - `repayment.has_overdue_installment(student)`
9. `eligibility.assess` returns per-rule outcomes, reasons and the rule-set version (FR-002.1, FR-002.6). `applications` stores the assessment with its full input snapshot, so the decision can be reproduced (NFR-003.4).
10. `applications` applies FR-002.2. In this scenario every rule passes, so the application is **approved**:
    - **Deny branch:** stores the reasons for every rule that failed (FR-002.3).
    - **Escalate branch:** calls `review.open(kind=escalation)`.
11. `ledger.reserve` writes a reservation entry using the balance read in step 8 (FR-002.5). Because the check and the reservation share one transaction, concurrent approvals cannot overdraw the fund (NFR-001.1).
12. `agreements.generate` creates the LoanAgreement with the amount and repayment terms, status `pending_signature` (FR-004.1).
13. `audit.append` records the application, each rule outcome, the decision and the reservation, then the transaction commits. The student sees "approved" and is prompted to sign (AC-01). The target is under 5 s (NFR-005.1); the SIS timeout alone is 3 s.
14. The student signs. The e-signature port records consent, intent, the PDF and its hash (NFR-004.1, NFR-004.2). In one transaction, `agreements.sign`:
    - checks the signing window against `Clock`
    - compare-and-sets the status to `signed`
    - calls `ledger.disburse` to convert the reservation to disbursed principal (FR-002.5)
    - calls `repayment.create_loan` to create the Loan and RepaymentSchedule with amounts but no dates yet (FR-005.1)
    - calls `disbursement.create_pending`
    - writes audit records
15. `jobs` calls `disbursement.post_pending`, which posts to the SIS with the Disbursement ID as idempotency key within 1 business day (NFR-005.3). On success it records the posting time and calls `repayment.set_due_dates(posted_at)`; the first installment is due 30 days later (FR-005.1).

The officer path (FR-003) re-enters at step 10. A web route calls `applications.resolve_review`, which:
- calls `review.resolve`, where a rationale is mandatory (FR-003.2);
- on approve, re-reads the SIS and rechecks the gap (FR-003.6);
- then runs steps 11–13 in one transaction, where a reservation the fund cannot cover is refused (FR-003.3).

## 4. Design decisions

| Decision | Reason |
|---|---|
| **Scope: full system as independently buildable modules**, each testable with its neighbours mocked | User constraint. The module boundaries follow the FR groups (FR-001 to FR-006, NFR-003), so each FR group can be built and tested on its own. |
| **Modular monolith, one FastAPI app, hexagonal ports and adapters** | The monolith is a **preference**: the spec forces no deployment shape, and one process is the simplest fit for local Docker. Ports are a user constraint; the SIS as source of truth (FR-001.5) and the payment tokenisation (NFR-002.4) are the integrations they isolate. |
| **Jinja + HTMX for student flow and officer dashboard** | **Preference.** The spec needs a student UI (AC-01) and a dashboard (FR-003.1) but no particular technology. HTMX covers the live amount validation in AC-01 without a separate frontend. |
| **No real auth: `get_current_user()` from a dev header or user-switcher; role-declared endpoints; queries scoped to the current user; actor on every AuditRecord** | User constraint. Role and ownership scoping implement NFR-002.2. The actor field implements NFR-003.2. NFR-002.3 (MFA) is deferred to the real identity adapter. |
| **Integer cents in storage, Decimal in domain** | NFR-001.3. Remainder cents go to the final installment (FR-005.1) and need exact arithmetic. |
| **Fund balances derived from an append-only double-entry ledger** (accounts per fund: Available, Reserved, Disbursed principal) | NFR-001.4 becomes a sum over entries that can be tested. It also gives reservation and release (FR-002.5, FR-004.3) and repayment crediting (FR-006.2) one mechanism. |
| **Atomic reservation via a SQLite `BEGIN IMMEDIATE` transaction, portable to Postgres** | NFR-001.1. On Postgres the same unit of work becomes `SELECT … FOR UPDATE` on the fund row. |
| **Append-only AuditRecord table, with SQLite triggers blocking UPDATE and DELETE** | NFR-003.3. |
| **SHA-256 hash chain over AuditRecords** | The "tamper-evident" title of NFR-03. Triggers stop edits through the app; the chain detects edits made outside it. |
| **Eligibility rules as Python classes, with thresholds in a versioned rule set; version recorded on every assessment** | FR-002.6 (configurable, versioned thresholds), NFR-003.2, NFR-003.4. |
| **Mock SIS as a separate container with outage, latency and incomplete-data toggles** | FR-001.4, FR-003.6 and NFR-005.2 describe real-network failure modes. Running the mock over real HTTP is the only way to test the 3 s timeout honestly. |
| **Payments, e-signature and notifications as in-process mock adapters** | User constraint (no paid services). E-sign records consent, a PDF and a hash per NFR-004.1 and NFR-004.2. The notification outbox satisfies FR-005.3, and the mock inbox page makes it visible (the page itself is a **preference**). |
| **APScheduler in-process for expiry, reminders, overdue flags and disbursement posting** | FR-003.5, FR-004.3, FR-005.3, FR-006.3, NFR-005.3 all need time-triggered work. In-process is the simplest option for one local container. |
| **Injectable Clock** | Every time-based FR above. Deterministic tests need controllable time. |
| **Admin "advance time" endpoint** | **Preference** (demo convenience). No requirement asks for it. It moves the Clock only, and the move is audited like a configuration change (NFR-003.1). |
| Deadlines checked at the moment of action as well as by jobs | FR-002.4, FR-003.5, FR-004.3: the spec states these as rules, not as job behaviours, so job lag must not change outcomes. |
| All SIS calls made before the write transaction opens | NFR-005.1 and NFR-005.2. A 3 s network wait must not hold SQLite's single write lock. |
| Eligibility is pure; `applications` gathers its inputs and stores them with the assessment | NFR-003.4 (decision reproducible from records). NFR-001.1 (the fund balance is read in the same transaction as the reservation). |
| Partial unique index on active application/loan per (student, term) | FR-001.6 under concurrent submits. |
| Compare-and-set status transitions on LoanAgreement and ExceptionReview | Sign vs expire (FR-004.3) and officer resolve vs deadline expiry (FR-003.5) can race; only one transition may win. |
| Idempotency keys stored with ledger entries, payment credits and SIS postings | NFR-001.2. |
| AuditRecord written in the same transaction as the state change it describes | NFR-003.1: a committed change without its audit record would break completeness. |
| `review` does not depend on `applications`; `applications` calls `review` | Avoids a dependency cycle. It also keeps the only code that changes application status in one module (FR-002.2, FR-003.5). |

## 5. Constraints and known limits

### Implementation Constraints
- Python 3.12 + FastAPI.
- SQLite via SQLAlchemy for the prototype.
- Runs locally via Docker Compose (app container + mock SIS container); no paid services.
- Synthetic test data only; no real student PII or records.
- SIS, payments and identity/SSO (plus e-signature and notifications) are mocked behind ports, so real integrations can replace them.
- Regulatory compliance is out of scope for the prototype; future requirements and where they plug in are listed below.

### Compliance deferred, and where it will live
| Future requirement | Spec ref | Where it plugs in |
|---|---|---|
| Real SSO and officer MFA | NFR-002.3 | Replace the identity adapter; `get_current_user()` keeps its signature |
| Encryption at rest | NFR-002.1 | Storage layer (Postgres with disk/TDE encryption, or SQLCipher); TLS at the container ingress |
| FERPA / GLBA handling and quarterly access reviews | NFR-002.5 | Role definitions in `identity`; access-review reports from `audit`. The review itself is an institutional process, not code |
| PCI DSS tokenisation | NFR-002.4 | Real processor adapter behind the payments port; the domain already stores only tokens |
| ESIGN/UETA-compliant signatures | NFR-004.1 | Real e-signature adapter behind the existing port; the consent and intent fields already exist |
| Counsel-approved agreement text and lending disclosures | NFR-004.4 | Agreement templates in `agreements`; a content change, not a structural one |

### What this design does not handle
- **Availability (NFR-005.4).** One process with one SQLite file has no redundancy, so 99.9% is not achievable as built.
- **Write throughput.** SQLite allows one writer at a time. That is fine for a prototype; peak-week load would need Postgres.
- **Multiple app instances.** APScheduler in-process would run every job once per instance, and the hash chain assumes appends are serialised. Scaling out needs a single-leader scheduler (or DB advisory lock) and a lock around chain appends.
- **Encryption at rest.** The SQLite file is unencrypted (synthetic data only).
- **SIS outages.** By design, an SIS outage blocks applications and officer approvals (FR-001.4, FR-003.6). The system does not queue them.
- **Multiple loan funds.**

### What would change if the requirements grew
- **Interest or fees.** New ledger accounts (interest receivable, fee income), a schedule calculator in `repayment`, and the NFR-001.4 invariant extended to cover them.
- **More than one loan per term.** Drop the partial unique index, and the gap calculation (FR-001.1) must subtract outstanding loans.
- **Rules needing new data** (e.g. registration holds). Add the field to the eligibility input snapshot and a rule class; existing assessments stay reproducible because the snapshot is stored.
- **Higher volume or real integrations.** Swap SQLite for Postgres (same unit-of-work boundary), move jobs to an external scheduler, and make SIS posting asynchronous with callbacks. The module boundaries do not change.
