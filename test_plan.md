# Test Plan: Tuition Gap Micro-Loan Service

Sources: `spec.md` (requirements, acceptance criteria) and `architecture.md` (module boundaries, ports, injectable Clock). No implementation code was read. All expected values below were computed by hand from the spec.

---

## 0. Conventions

### 0.1 Test IDs

| Prefix | Area |
|---|---|
| `AC01-nn`, `AC02-nn` | Refined acceptance-criterion scenarios (same order as in spec.md) |
| `AMT-nn` | Requested-amount limits (FR-001.3) |
| `GAP-nn` | Tuition-gap calculation (FR-001.1) |
| `ACT-nn` | One active application/loan per term (FR-001.6) |
| `SIS-nn` | SIS retrieval, failures, timeout (FR-001.2, FR-001.4, FR-003.6, NFR-005.2) |
| `ELG-nn` | Eligibility rules and decision precedence (FR-002.1–002.3, FR-002.6) |
| `APL-nn` | Appeals (FR-002.4) |
| `FND-nn` | Fund reservation, ledger, idempotency (FR-002.5, FR-006.1–006.2, NFR-001) |
| `REV-nn` | Officer review and dashboard (FR-003) |
| `AGR-nn` | Agreement, signing, expiry, disbursement (FR-004, NFR-004, NFR-005.3) |
| `PAY-nn` | Repayment, reminders, overdue (FR-005, FR-006.3) |
| `AUD-nn` | Audit trail (NFR-003, FR-003.4) |
| `SEC-nn` | Identity and access (NFR-002.2) |
| `CFG-nn` | Versioned configuration (FR-002.6, NFR-003.1) |
| `PRF-nn` | Timing (NFR-005.1) |

Tests tagged **`[extra: <req>]`** were added by walking the gap checklist; they are not derived from an acceptance criterion, and the tag names the requirement they probe. Tests tagged **`[TBD: SG-nn]`** have an expected value the spec does not determine; the matching item is in §6 Spec gaps. Those expected values are deliberately left open.

Each rejection test names its **control** (a valid request of the same shape that is accepted). Each limit has an **inside** and an **outside** case.

### 0.2 Standard assertions

- **"nothing was created"** means, compared with the state before the request:
  - LoanApplication count for the student is unchanged;
  - no new EligibilityAssessment, ExceptionReview, LoanAgreement, Loan, RepaymentSchedule, Disbursement or Payment;
  - no new ledger entry, and LoanFund F1 available balance is unchanged;
  - no new state-change AuditRecord;
  - no write call was made to the SIS port.
- **"no money moved"** (used for denials, where an application and an assessment *are* created by design) means: no ledger entry, no LoanAgreement, no Disbursement, no SIS posting, and F1 available balance is unchanged.

### 0.3 Fixtures (all synthetic)

**Clock.** Injected. Default `2026-08-03 09:00 America/Chicago` (a Monday). Tests that move time say so.

**Term.** `Fall 2026`, SIS payment deadline `2026-08-24`.

**Configuration (rule-set version `v1`).**

| Key | Value | Source |
|---|---|---|
| min loan | $100.00 | FR-001.3 default |
| max loan | $1,500.00 | FR-001.3 default |
| appeal window | 7 days | FR-002.4 default |
| signing window | 7 days | FR-004.3 default |
| installments | 4 | FR-005.1 default |
| first due | 30 days after posting | FR-005.1 |
| overdue after | 10 days | FR-006.3 default |
| reminder lead | **3 days (set by the test; spec gives no default, SG-14)** | FR-005.3 |
| enrollment | ≥6 Pass, 3–5 Escalate, <3 Fail | FR-002.6 |
| SAP | Meeting Pass, Warning Escalate, Suspended Fail | FR-002.6 |

**LoanFund F1.** Initial capital $10,000.00, no entries. Available = $10,000.00.

**Users.** Students `stu-001` (S1), `stu-002` (S2); Financial Aid Officer `off-001` (O1).

**Mock SIS record, baseline for S1 (and S2 unless stated):**

| Field | Value |
|---|---|
| TuitionCharge outstanding balance (Fall 2026) | $4,000.00 |
| AidAwards accepted, not yet disbursed | $3,400.00 |
| Enrollment credits | 12 |
| SAP status | Meeting |
| Registration hold | Yes |
| Payment deadline | 2026-08-24 |

Baseline gap = 4,000.00 − 3,400.00 = **$600.00**. Max requestable = min(600.00, 1,500.00) = **$600.00**. S1 has no other loans.

---

## 1. Refined acceptance criteria

### AC-01 Submit a Loan Application

```gherkin
Feature: Apply for a tuition microloan

  Background:
    Given the Clock is 2026-08-03 09:00 America/Chicago
    And I am logged in as Student stu-001
    And the SIS reports for Fall 2026: balance $4,000.00, accepted undisbursed aid $3,400.00,
        12 credits, SAP "Meeting", registration hold Yes, payment deadline 2026-08-24
    And LoanFund F1 has available balance $10,000.00
    And I have no LoanApplication or Loan

  @AC01-01
  Scenario: Student sees their calculated tuition gap
    When I start a loan application for Fall 2026
    Then I see a tuition gap of $600.00
    And I see a maximum loan amount of $600.00
    And no LoanApplication exists for stu-001            # FR-001.6: start creates nothing
    And the SIS port was called exactly 1 time

  @AC01-02
  Scenario: Eligible student is automatically approved
    Given I have started a loan application for Fall 2026
    When I request $600.00 and submit
    Then the EligibilityAssessment has: Enrollment=Pass, SAP=Pass, Fund availability=Pass,
         No overdue loans=Pass, rule-set version "v1"
    And my application status is "approved"
    And I am prompted to review and sign my LoanAgreement
    And the LoanAgreement shows amount $600.00, 0% interest, $0.00 fees,
        4 installments of $150.00, status "pending_signature"
    And F1 has reserved $600.00 and available balance $9,400.00
    And no Disbursement exists yet                        # FR-004.2
    And the SIS port was called exactly 2 times (start + submit)   # FR-001.2

  @AC01-03
  Scenario: Ineligible student is automatically denied
    Given the SIS reports 2 credits (all other baseline values unchanged)
    And I have started a loan application for Fall 2026
    When I request $600.00 and submit
    Then the EligibilityAssessment has: Enrollment=Fail, SAP=Pass, Fund availability=Pass,
         No overdue loans=Pass
    And my application status is "denied"
    And I see exactly one denial reason, identifying the enrollment requirement
    And the SIS still reports registration hold Yes      # see SG-A1
    And no money moved
    # Control: AC01-02 (same request, 12 credits)

  @AC01-04
  Scenario: Edge-case application is escalated for manual review
    Given the SIS reports 4 credits (all other baseline values unchanged)
    And I have started a loan application for Fall 2026
    When I request $600.00 and submit
    Then the EligibilityAssessment has: Enrollment=Escalate, SAP=Pass, Fund availability=Pass,
         No overdue loans=Pass
    And my application status is "escalated" and I see that it is under review
    And one open ExceptionReview of kind "escalation" exists for my application
    And no money moved                                    # reservation only on approval (FR-002.5)

  @AC01-05
  Scenario: Student cannot request more than their tuition gap
    Given I have started a loan application for Fall 2026
    When I request $900.00
    Then I see "amount exceeds your tuition gap of $600.00"
    And I cannot submit the application
    And nothing was created
    # $900.00 is within min/max ($100–$1,500); only the gap is violated.
    # Control: AC01-02. Inside/outside: AMT-01 / AMT-02.
```

### AC-02 Automated Loan Eligibility Decisions

```gherkin
Feature: Automated eligibility decision

  Background:
    Given the Clock is 2026-08-03 09:00 America/Chicago
    And I am logged in as Student stu-001
    And the SIS reports balance $4,000.00 and accepted undisbursed aid $3,400.00 for Fall 2026
    And I have started a loan application for Fall 2026 and requested $600.00
    And LoanFund F1 has available balance $10,000.00
    And I have no overdue installment on any loan

  @AC02-01
  Scenario: Part-time enrollment is escalated for manual review
    Given the SIS reports 4 credits and SAP "Meeting"
    When I submit my application
    Then my application status is "escalated"
    And officer off-001's dashboard shows my review with triggering rule "Enrollment" only
    And the dashboard row shows tuition gap $600.00 and current awards $3,400.00
    And no money moved

  @AC02-02
  Scenario: A failed rule takes priority over an escalation
    Given the SIS reports 4 credits and SAP "Suspended"
    When I submit my application
    Then the assessment has Enrollment=Escalate, SAP=Fail
    And my application status is "denied"
    And no ExceptionReview exists for my application
    And I see exactly one denial reason, identifying the SAP requirement
    And no money moved
    # Control: AC02-01 (same credits, SAP "Meeting" → escalated, not denied)

  @AC02-03
  Scenario: Denial lists every failed eligibility rule
    Given the SIS reports 2 credits and SAP "Suspended"
    When I submit my application
    Then the assessment has Enrollment=Fail, SAP=Fail, Fund availability=Pass, No overdue loans=Pass
    And my application status is "denied"
    And I see exactly two denial reasons: the enrollment requirement and the SAP requirement
    And no money moved
    # Deliberately two faults: this tests listing (FR-002.3), not a single rejection.
    # Single-fault versions: ELG-04 (credits only), ELG-07 (SAP only).
```

---

## 2. Inside/outside and control cases for the AC limits

All use the AC-01 Background unless a row overrides it. "Accepted" for a submit means: application created and, with all rules passing, approved with the amount reserved.

### 2.1 Requested amount (FR-001.3, FR-006.1)

```gherkin
  Scenario Outline: Requested amount limits
    Given the SIS reports balance <balance> and accepted undisbursed aid <aid> (gap <gap>)
    And I have started a loan application for Fall 2026
    When I request <amount> and submit
    Then the result is <result>
    And F1 available balance is <available>

    Examples:
      | id     | limit        | balance   | aid       | gap       | amount    | result                                   | available  |
      | AMT-01 | gap (inside) | 4,000.00  | 3,400.00  | 600.00    | 600.00    | approved, $600.00 reserved               | 9,400.00   |
      | AMT-02 | gap (out)    | 4,000.00  | 3,400.00  | 600.00    | 600.01    | rejected "exceeds your tuition gap of $600.00"; nothing was created | 10,000.00 |
      | AMT-03 | min (inside) | 4,000.00  | 3,400.00  | 600.00    | 100.00    | approved, $100.00 reserved               | 9,900.00   |
      | AMT-04 | min (out)    | 4,000.00  | 3,400.00  | 600.00    | 99.99     | rejected "below minimum of $100.00"; nothing was created | 10,000.00 |
      | AMT-05 | max (inside) | 5,000.00  | 3,000.00  | 2,000.00  | 1,500.00  | approved, $1,500.00 reserved             | 8,500.00   |
      | AMT-06 | max (out)    | 5,000.00  | 3,000.00  | 2,000.00  | 1,500.01  | rejected "exceeds maximum of $1,500.00"; nothing was created | 10,000.00 |
```

- Controls: AMT-02 → AMT-01; AMT-04 → AMT-03; AMT-06 → AMT-05.
- AMT-06 is single-fault: $1,500.01 is under the $2,000.00 gap.

`AMT-07` (FR-001.3 display): with the AMT-05 SIS values, starting an application shows gap $2,000.00 and maximum loan amount **$1,500.00**.

### 2.2 Tuition gap ≤ 0 (FR-001.1)

| id | Balance | Accepted undisbursed aid | Gap | Expected |
|---|---|---|---|---|
| GAP-01 (inside) | 3,400.01 | 3,400.00 | 0.01 | Start allowed; gap $0.01 shown; max loan shown $0.01. What the student can then submit is undetermined `[TBD: SG-01]` |
| GAP-02 (outside) | 3,400.00 | 3,400.00 | 0.00 | Cannot apply; nothing was created. Control: AC01-01 |
| GAP-03 (outside) | 3,000.00 | 3,400.00 | −400.00 | Cannot apply; nothing was created. Control: AC01-01 |
| GAP-04 `[extra: FR-001.1]` | 4,000.00 | 3,400.00 accepted + $500.00 offered-not-accepted | 600.00 | Gap shows $600.00 (unaccepted aid is not subtracted) |

`GAP-05` (inside for FR-001.3 min, gap side) `[extra: FR-001.1/001.3]`: balance 3,500.00, aid 3,400.00, gap $100.00, request $100.00 → approved, F1 available 9,900.00.

### 2.3 Eligibility thresholds (FR-002.6)

The background is AC-02. Only the listed field changes. All others stay at baseline: 12 credits, Meeting, fund $10,000.00, no overdue.

| id | Field | Value | Rule outcome | Application | Money | Pairs with |
|---|---|---|---|---|---|---|
| ELG-01 | credits | 6 | Enrollment Pass | approved | $600.00 reserved, available 9,400.00 | inside of ELG-02 |
| ELG-02 | credits | 5 | Enrollment Escalate | escalated | no money moved | outside of ELG-01 |
| ELG-03 | credits | 3 | Enrollment Escalate | escalated | no money moved | inside of ELG-04 |
| ELG-04 | credits | 2 | Enrollment Fail | denied, 1 reason (enrollment) | no money moved | outside of ELG-03; control ELG-03 |
| ELG-05 | SAP | Meeting | SAP Pass | approved | $600.00 reserved | control for ELG-06/07 |
| ELG-06 | SAP | Warning | SAP Escalate | escalated | no money moved | — |
| ELG-07 | SAP | Suspended | SAP Fail | denied, 1 reason (SAP) | no money moved | control ELG-05 |
| ELG-08 | fund available | 600.00 | Fund Pass | approved | available 0.00 | inside of ELG-09 |
| ELG-09 | fund available | 599.99 | Fund Fail | denied, 1 reason (fund) | available stays 599.99 | outside; control ELG-08 |
| ELG-10 | SAP | `"Probation"` (not one of the three) | `[TBD: SG-02]` | `[TBD: SG-02]` | `[extra: FR-002.6]` |

For ELG-08 and ELG-09, F1 initial capital is set to the stated value.

**No overdue loans (FR-002.6, FR-006.3).** S1 also has an active Spring 2026 loan. Its installment was due `2026-07-24` and is unpaid. Clock = assessment time.

| id | Clock | Days past due | Expected rule | Application |
|---|---|---|---|---|
| ELG-11 (inside) | 2026-08-02 09:00 | 9 | Pass | approved |
| ELG-12 (boundary) | 2026-08-03 09:00 | 10 | `[TBD: SG-03]` | `[TBD: SG-03]` |
| ELG-13 (outside) | 2026-08-04 09:00 | 11 | Fail | denied, 1 reason (overdue loan); no money moved. Control ELG-11 |
| ELG-14 `[extra: FR-002.6]` | 2026-08-04 09:00 | installment paid 2026-07-30 | Pass | approved |
| ELG-15 `[extra: FR-006.3 / arch "computed at assessment time"]` | 2026-08-04 09:00 | 11, but overdue job has **not** run | Fail | denied. Control ELG-11 |

### 2.4 Decision precedence (FR-002.2, FR-002.3)

| id | Enrollment | SAP | Fund | Overdue | Expected decision | Reasons shown / review triggers |
|---|---|---|---|---|---|---|
| ELG-20 | Pass (12) | Pass | Pass | Pass | approved | — |
| ELG-21 | Escalate (4) | Escalate (Warning) | Pass | Pass | escalated | review lists Enrollment and SAP as triggers |
| ELG-22 `[extra: FR-002.2]` | Escalate (4) | Pass | Fail (599.99) | Pass | denied | 1 reason: fund. Escalate does not survive a Fail |
| ELG-23 `[extra: FR-002.3]` | Fail (2) | Fail (Suspended) | Fail (599.99) | Fail (11 days) | denied | exactly 4 reasons, one per rule (all rules evaluated even after the first Fail) |
| ELG-24 `[extra: FR-002.6]` | Pass | Pass | Fail | Pass | denied | the Fund rule's outcome is never "Escalate", even when the shortfall is $0.01 |

---

## 3. Extra cases from the gap checklist

### 3.1 Boundaries: SIS timeout (NFR-005.2, FR-001.4, FR-003.6)

| id | When | SIS latency | Expected |
|---|---|---|---|
| SIS-01 (inside) | start | 2.9 s | gap $600.00 shown |
| SIS-02 (outside) | start | 3.1 s | "try again later"; nothing was created. Control SIS-01 |
| SIS-03 (inside) | submit | 2.9 s | approved, $600.00 reserved |
| SIS-04 (outside) | submit | 3.1 s | "try again later"; nothing was created. Control SIS-03 |
| SIS-05 (inside) | officer approval of AC01-04's review | 2.9 s | approval recorded |
| SIS-06 (outside) | officer approval of AC01-04's review | 3.1 s | "try again later"; review stays open; no reservation, agreement or audit of a decision. Control SIS-05 |

### 3.2 Errors: SIS outage and incomplete data `[extra: FR-001.4, FR-003.6]`

| id | Condition | Expected | Control |
|---|---|---|---|
| SIS-10 | SIS outage toggle on, at start | "try again later"; nothing was created | AC01-01 |
| SIS-11 | Start succeeds; outage at submit | "try again later"; nothing was created | AC01-02 |
| SIS-12 | Payload missing SAP status (all else baseline) | "try again later"; nothing was created | AC01-02 |
| SIS-13 | Payload missing payment deadline | "try again later"; nothing was created | AC01-02 |
| SIS-14 | Outage at officer approval | "try again later"; review open; nothing was created | REV-02 |
| SIS-15 | Outage at officer **denial** | `[TBD: SG-04]` (FR-003.6 says the officer "may still deny" but only for gap failures) | — |

### 3.3 State: data changes between start and submit `[extra: FR-001.2, FR-001.5]`

| id | SIS at start | SIS at submit | Request | Expected |
|---|---|---|---|---|
| SIS-20 | gap 600.00 | balance 4,000.00, aid 3,500.00 (gap 500.00) | 600.00 | rejected "exceeds your tuition gap of $500.00"; nothing was created |
| SIS-21 (control) | gap 600.00 | gap 500.00 | 500.00 | approved, $500.00 reserved, F1 available 9,500.00 |
| SIS-22 | 12 credits | 4 credits | 600.00 | escalated (assessment uses the submit-time data) |

### 3.4 State: one active application/loan per term (FR-001.6)

S1 is in the stated prior state for Fall 2026 and submits a new $600.00 request.

| id | Prior state (Fall 2026) | Expected |
|---|---|---|
| ACT-01 | none | accepted (control for ACT-02..05) |
| ACT-02 | application approved, pending signature | rejected "you already have an active application"; nothing was created |
| ACT-03 | application escalated (review open) | rejected; nothing was created |
| ACT-04 | Loan signed, $450.00 outstanding | rejected; nothing was created |
| ACT-05 | Loan fully repaid ($0.00 outstanding), SIS gap now $300.00, request $300.00 | accepted |
| ACT-06 | application denied, no appeal | accepted |
| ACT-07 | application expired (unsigned) | accepted |
| ACT-08 | application denied, appeal pending | `[TBD: SG-05]` |
| ACT-09 | active Loan for **Spring 2026**, not overdue | accepted (limit is per term) |
| ACT-10 | none; S1 starts but never submits | no LoanApplication exists; a later start + submit is accepted |

### 3.5 Concurrency `[extra: FR-001.6, NFR-001.1, NFR-001.2]`

| id | Setup | Action | Expected |
|---|---|---|---|
| FND-01 | F1 available 1,000.00; S1, S2 both baseline | S1 and S2 submit $600.00 simultaneously | exactly one approved (reserved 600.00); the other is denied with reason fund; F1 available 400.00; never negative |
| FND-02 (control) | F1 available 1,200.00 | same | both approved; F1 available 0.00 |
| FND-03 | S1 baseline | two simultaneous submits by S1, $600.00 each | exactly 1 LoanApplication; 1 reservation of 600.00; F1 available 9,400.00; second gets "already active" |
| FND-04 | S1 approved | sign request sent twice (retry, same idempotency key) | 1 signature, 1 disburse entry, 1 Disbursement; reserved 0.00; disbursed principal 600.00 |
| FND-05 | Disbursement pending | SIS posting retried after the mock times out the response but records the post | the SIS shows exactly 1 posting for that Disbursement ID |
| FND-06 | Loan 600.00 | payment of 150.00 credited twice with the same idempotency key | 1 credit; F1 available rises by 150.00 once |
| AGR-20 | approved at 2026-08-03 09:00 | sign and expiry job run together at 2026-08-10 09:00 | exactly one wins: either (signed, disbursed 600.00) or (expired, released 600.00). Never both, never neither |
| REV-20 | escalated review, deadline 2026-08-24 | officer approve and expiry job at the deadline | exactly one resolution recorded |

### 3.6 Fund ledger (FR-002.5, FR-004.3, FR-006.2, NFR-001.4)

| id | Step | F1 available | Reserved | Disbursed principal | Repaid principal |
|---|---|---|---|---|---|
| FND-10 | start (capital 10,000.00) | 10,000.00 | 0.00 | 0.00 | 0.00 |
| | S1 approved 600.00 | 9,400.00 | 600.00 | 0.00 | 0.00 |
| | S1 signs | 9,400.00 | 0.00 | 600.00 | 0.00 |
| | S2 approved 400.00 | 9,000.00 | 400.00 | 600.00 | 0.00 |
| | S2 expires unsigned | 9,400.00 | 0.00 | 600.00 | 0.00 |
| | S3 approved 300.00 (left pending) | 9,100.00 | 300.00 | 600.00 | 0.00 |
| | S1 pays 150.00 | 9,250.00 | 300.00 | 600.00 | 150.00 |

The invariant is checked after every step: 10,000.00 − reserved − disbursed + repaid = available. At the final step that is 10,000 − 300 − 600 + 150 = 9,250.00. There is zero unexplained discrepancy.

`FND-11` `[extra: NFR-001.3]`: a loan of $100.03 has installments 25.00, 25.00, 25.00, 25.03. Pay all four. Repaid principal = $100.03 exactly, outstanding = $0.00, and the Loan is "fully repaid". The NFR-001.4 invariant holds with zero discrepancy. Binary floating point can leave a residue here.

### 3.7 Appeals (FR-002.4)

Decision: AC01-03's denial at `2026-08-03 09:00`.

| id | Clock | Request | Expected |
|---|---|---|---|
| APL-01 (inside) | 2026-08-10 08:59 | appeal, explanation "Adding 4 credits on Aug 5" | accepted; 1 ExceptionReview kind "appeal"; still exactly 1 EligibilityAssessment (rules not re-run) |
| APL-02 (outside) | 2026-08-10 09:01 | same | rejected "appeal window closed"; nothing was created. Control APL-01 |
| APL-03 (boundary) | 2026-08-10 09:00 | same | `[TBD: SG-06]` |
| APL-04 | 2026-08-04 | appeal with empty explanation | accepted (explanation optional) |
| APL-05 | 2026-08-05 | second appeal after APL-04 | rejected "only one appeal allowed"; nothing new created. Control APL-04 |
| APL-06 `[extra: FR-002.4 state]` | 2026-08-04 | appeal on AC01-02's **approved** application | rejected; nothing was created. Control APL-04 |
| APL-07 `[extra: FR-002.4 state]` | 2026-08-04 | appeal on AC01-04's **escalated** application | rejected; nothing was created. Control APL-04 |
| APL-08 `[extra: NFR-002.2]` | 2026-08-04 | S2 appeals S1's denied application | rejected; no ExceptionReview; S1's application unchanged. Control APL-04 |

### 3.8 Officer review and dashboard (FR-003)

Review under test (unless stated): AC01-04's escalation (S1, 4 credits, $600.00 requested, deadline 2026-08-24). Clock is 2026-08-05 10:00.

| id | Action by O1 | Expected | Control |
|---|---|---|---|
| REV-01 | approve, rationale "" | rejected "rationale required"; review open; nothing was created | REV-02 |
| REV-02 | approve, rationale "Final term; 4 credits completes degree" | application approved; $600.00 reserved; F1 available 9,400.00; LoanAgreement pending_signature; review resolved | — |
| REV-03 | deny, rationale "" | rejected; review open; nothing was created | REV-04 |
| REV-04 | deny, rationale "Below full-time; no justification" | application denied; review resolved; no money moved | — |
| REV-05 `[extra: FR-003.2 input]` | approve, rationale "   " (whitespace only) | `[TBD: SG-07]` | REV-02 |
| REV-06 | approve an appeal of a SAP=Suspended denial (APL-01 style) with rationale | approved, $600.00 reserved (Fail may be overridden) | — |
| REV-07 | approve an appeal of a Fund=Fail denial (ELG-09), fund still 599.99 | rejected "loan fund cannot cover"; review open; nothing was created. Deny is still possible | REV-08 |
| REV-08 | same as REV-07 but F1 restored to 600.00 before approval | `[TBD: SG-08]`: FR-003.3 forbids overriding the Fund rule's original Fail even if the fund now covers it | — |
| REV-09 | approve escalation; F1 drained to 599.99 since submission | rejected "loan fund cannot cover"; nothing was created | REV-10 |
| REV-10 (inside) | approve escalation; F1 at exactly 600.00 | approved; F1 available 0.00 | — |
| REV-11 | approve; SIS now reports aid 3,400.01 (gap 599.99) | rejected "requested amount exceeds current tuition gap of $599.99"; nothing was created | REV-12 |
| REV-12 (inside) | approve; SIS gap still 600.00 | approved | — |
| REV-13 | deny when the recalculated gap is 599.99 | denial recorded (deny still allowed) | — |
| REV-14 `[extra: FR-003 state]` | approve an already-resolved review | rejected; no second decision or audit record | REV-02 |
| REV-15 `[extra: NFR-002.2]` | S1 (Student) calls the approve endpoint | forbidden; nothing was created | REV-02 |

**Deadline expiry (FR-003.5).** Deadline 2026-08-24.

| id | Clock | Expected |
|---|---|---|
| REV-30 (inside) | 2026-08-23 12:00, O1 approves with rationale | approved |
| REV-31 (outside) | 2026-08-25 09:00, job has run | review expired; application denied with reason exactly "Review not completed before the payment deadline."; no money moved |
| REV-32 (outside) | 2026-08-25 09:00, job has **not** run; O1 tries to approve | rejected at the moment of action; nothing was created (architecture §2 Time). Control REV-30 |
| REV-33 (boundary) | 2026-08-24 12:00 | `[TBD: SG-09]` |

**Dashboard listing (FR-003.1).** Seeded reviews:

| Review | Kind | Student deadline | Status |
|---|---|---|---|
| R1 | escalation | 2026-08-24 | open |
| R2 | appeal | 2026-08-17 | open |
| R3 | escalation | 2026-09-01 | open |
| R4 | appeal | 2026-08-10 | resolved |
| R5 | escalation | 2026-08-12 | expired |

- `REV-40`: the dashboard lists exactly R2, R1, R3, in that order. R4 and R5 are absent.
- `REV-41`: each row shows the student's tuition gap, current awards, the triggering rule(s) (escalation) or the failed rules (appeal), and the kind.
- `REV-42` `[extra: FR-003.1 listing]`: two open reviews with the same deadline → order `[TBD: SG-10]`.
- `REV-43` `[extra: FR-003.1 listing]`: no open reviews → empty list, no error.

### 3.9 Agreement, signing, disbursement (FR-004, FR-002.5, NFR-004, NFR-005.3)

Approval: AC01-02 at `2026-08-03 09:00` (Mon).

| id | Action / clock | Expected | Control |
|---|---|---|---|
| AGR-01 | view agreement | amount $600.00; 0% interest; $0.00 fees; 4 installments $150.00 each; due dates not yet set | — |
| AGR-02 (inside) | sign at 2026-08-10 08:59 with consent + intent | signed; reserved 0.00, disbursed 600.00, available 9,400.00; Loan + schedule created; 1 Disbursement pending | — |
| AGR-03 (outside) | sign at 2026-08-10 09:01 (job not run) | rejected "signing window expired"; no Disbursement; reservation released at expiry; F1 available 10,000.00 | AGR-02 |
| AGR-04 (boundary) | sign at 2026-08-10 09:00 | `[TBD: SG-06]` | — |
| AGR-05 | job at 2026-08-10 09:01, unsigned | application "expired"; F1 available 10,000.00; reserved 0.00 | — |
| AGR-06 | approved, never signed, clock 2026-08-05 | no Disbursement, no SIS posting (FR-004.2) | AGR-02 |
| AGR-07 `[extra: NFR-004.1 input]` | sign without the e-consent checkbox | rejected; still pending_signature; nothing was created | AGR-02 |
| AGR-08 `[extra: NFR-002.2]` | S2 signs S1's agreement | rejected; nothing was created | AGR-02 |
| AGR-09 | S1 downloads the signed agreement | file returned; SHA-256 of bytes = stored hash; consent record and signature timestamp stored (NFR-004.2, 004.3) | — |
| AGR-10 `[extra: NFR-004.3 identity]` | S2 downloads S1's agreement | rejected; no file content returned | AGR-09 |

**Posting within 1 business day (NFR-005.3).**

| id | Signed | Expected posted by | Check |
|---|---|---|---|
| AGR-11 | Mon 2026-08-03 10:00 | Tue 2026-08-04 10:00 | posted_at ≤ deadline; SIS balance for S1 falls by $600.00 to $3,400.00 |
| AGR-12 `[extra: NFR-005.3 time]` | Fri 2026-08-07 10:00 | Mon 2026-08-10 10:00 | weekend skipped. Holiday handling `[TBD: SG-11]` |
| AGR-13 `[extra: errors]` | Mon 2026-08-03 10:00, SIS outage until 2026-08-03 18:00 | Tue 2026-08-04 10:00 | first attempt fails and stays pending; retry posts once with the same idempotency key |

### 3.10 Repayment (FR-005, FR-006.2, FR-006.3)

**Schedule amounts (FR-005.1).** Base = amount ÷ 4 truncated to the cent; the remainder goes to installment 4.

| id | Loan | Inst 1 | Inst 2 | Inst 3 | Inst 4 | Sum check |
|---|---|---|---|---|---|---|
| PAY-01 | 600.00 | 150.00 | 150.00 | 150.00 | 150.00 | 600.00 |
| PAY-02 | 599.99 | 149.99 | 149.99 | 149.99 | 150.02 | 599.99 |
| PAY-03 | 100.03 | 25.00 | 25.00 | 25.00 | 25.03 | 100.03 |
| PAY-04 | 100.00 | 25.00 | 25.00 | 25.00 | 25.00 | 100.00 |
| PAY-05 | 1,500.00 | 375.00 | 375.00 | 375.00 | 375.00 | 1,500.00 |

The truncation reading is the only one that keeps "remainder added" non-negative. See SG-12.

**Due dates.**
- `PAY-10`: Disbursement posted 2026-08-04 → installment 1 due **2026-09-03** (Aug 4 + 30 days). Installments 2–4 `[TBD: SG-13]`.
- `PAY-11`: before posting (signed, not yet posted) → schedule has amounts and no due dates.

**Payments.** Loan 600.00, installment 1 due 2026-09-03.

| id | Action | Expected | Control |
|---|---|---|---|
| PAY-20 | one-time payment 150.00 (tokenised method) | installment 1 paid; outstanding 450.00; F1 repaid +150.00; F1 available +150.00 | — |
| PAY-21 | enrol in autopay | each installment charged on its due date; at 2026-09-03 outstanding 450.00 | — |
| PAY-22 | four payments of 150.00 | Loan "fully repaid"; outstanding 0.00; F1 repaid principal 600.00 | — |
| PAY-23 `[extra: FR-005.2 input]` | payment 0.00 | `[TBD: SG-15]` | PAY-20 |
| PAY-24 `[extra: FR-005.2 input]` | payment 700.00 on 600.00 outstanding | `[TBD: SG-15]` | PAY-22 |
| PAY-25 `[extra: NFR-002.4]` | after PAY-20 | database stores only a payment token; no card/bank number in any column | — |
| PAY-26 `[extra: NFR-002.2]` | S2 pays toward S1's loan | `[TBD: SG-16]` | PAY-20 |

**Reminders (FR-005.3).** Lead = 3 days. Installment 1 due 2026-09-03.

| id | Clock | Expected outbox for S1 |
|---|---|---|
| PAY-30 (outside, early) | 2026-08-30 | no reminder |
| PAY-31 (inside) | 2026-08-31 | exactly 1 reminder for installment 1 |
| PAY-32 `[extra: FR-005.3 idempotency]` | job runs twice on 2026-08-31 | still exactly 1 reminder |
| PAY-33 `[extra: FR-005.3 state]` | installment paid 2026-08-29, clock 2026-08-31 | `[TBD: SG-17]` |

**Overdue (FR-006.3).** Installment 1 due 2026-09-03, unpaid.

| id | Clock | Expected |
|---|---|---|
| PAY-40 (inside) | 2026-09-12 (9 days) | not overdue; Loan not flagged |
| PAY-41 (boundary) | 2026-09-13 (10 days) | `[TBD: SG-03]` |
| PAY-42 (outside) | 2026-09-14 (11 days) | installment overdue; Loan flagged for officer follow-up; AuditRecord written |
| PAY-43 `[extra: FR-006.3 state]` | paid 2026-09-10, clock 2026-09-14 | not overdue (control for PAY-42) |
| PAY-44 `[extra: FR-006.3 listing]` | after PAY-42 | where O1 sees the flagged Loan `[TBD: SG-18]` |

### 3.11 Audit trail (NFR-003, FR-003.4)

| id | Check | Expected |
|---|---|---|
| AUD-01 | after AC01-02 | AuditRecords exist for: application created, 4 rule outcomes, decision "approved", reservation 600.00. Each has actor "system", timestamp 2026-08-03 09:00, prior/new state, rule-set version "v1" |
| AUD-02 | after REV-02 | a record with actor off-001, timestamp 2026-08-05 10:00, decision "approve", rationale text, rule outcomes {Enrollment: Escalate, SAP: Pass, Fund: Pass, Overdue: Pass} |
| AUD-03 | after AGR-02, AGR-05, AGR-11, PAY-20 | one record each for signature, release, Disbursement, Payment |
| AUD-04 | app-level UPDATE and DELETE on any AuditRecord | both rejected; row unchanged |
| AUD-05 | edit record #3's `new_state` directly in the DB file, then run chain verify | verify fails and names record #3 as the first broken link |
| AUD-06 (control for AUD-05) | chain verify on untouched data | passes |
| AUD-07 | rebuild AC02-02's decision from AuditRecords alone (stored input snapshot + v1 thresholds) | same per-rule outcomes and "denied" |
| AUD-08 `[extra: NFR-003.1]` | force a failure after the reservation write, before commit | neither the reservation nor its AuditRecord persists; F1 available 10,000.00 |
| AUD-09 `[extra: NFR-003.1]` | rejected requests (AMT-02, REV-01) | no state-change AuditRecord written |

### 3.12 Identity and access (NFR-002.2)

| id | Actor | Request | Expected |
|---|---|---|---|
| SEC-01 | S2 | view S1's application | no S1 data returned |
| SEC-02 | S1 | submit with body/query param `student_id=stu-002` | application created for stu-001 only; stu-002 has none |
| SEC-03 | S1 | open the officer dashboard | forbidden |
| SEC-04 (control) | O1 | open the officer dashboard | listed reviews returned |
| SEC-05 | S1 | view own application | returned |

### 3.13 Input types `[extra: FR-001.3]`

All at baseline (gap 600.00). Control for each: AMT-01.

| id | Amount input | Expected |
|---|---|---|
| AMT-20 | `""` | rejected; nothing was created |
| AMT-21 | `"abc"` | rejected; nothing was created |
| AMT-22 | `"-100.00"` | rejected "below minimum of $100.00"; nothing was created |
| AMT-23 | `"0"` | rejected "below minimum of $100.00"; nothing was created |
| AMT-24 | `"600.001"` | `[TBD: SG-19]` |
| AMT-25 | `"600"` (no cents) | treated as 600.00; approved |

### 3.14 Versioned configuration `[extra: FR-002.6, NFR-003.1–003.2]`

| id | Action | Expected |
|---|---|---|
| CFG-01 | admin changes the enrollment Pass threshold from 6 to 9 → version "v2" | AuditRecord for the change (actor, prior 6, new 9) |
| CFG-02 | S1 with 6 credits submits after CFG-01 | Enrollment = Escalate; assessment records "v2" |
| CFG-03 | read an assessment made before CFG-01 | still shows "v1" and Pass for 6 credits (AUD-07 reproduces it) |
| CFG-04 | change max loan to 1,000.00; S1 with gap 2,000.00 requests 1,000.01 | rejected "exceeds maximum of $1,000.00"; nothing was created. Control: 1,000.00 approved |
| CFG-05 | config changed between S1's start and submit | which version applies `[TBD: SG-20]` |

### 3.15 Timing (NFR-005.1)

`PRF-01`: 200 submissions, with mock SIS latency 200 ms and baseline data → at least 190 (95%) show a decision within 5.0 s of submit.

---

## 4. Requirement → test coverage

| Requirement | Tests |
|---|---|
| FR-001.1 | AC01-01, GAP-01..05, SIS-20/21 |
| FR-001.2 | AC01-01, AC01-02, SIS-20..22 |
| FR-001.3 | AC01-05, AMT-01..07, AMT-20..25, CFG-04 |
| FR-001.4 | SIS-02, SIS-04, SIS-10..13 |
| FR-001.5 | SIS-20..22 |
| FR-001.6 | AC01-01, ACT-01..10, FND-03 |
| FR-002.1/002.2 | AC01-02..04, AC02-01..03, ELG-20..24 |
| FR-002.3 | AC01-03, AC02-02/03, ELG-23 |
| FR-002.4 | APL-01..08 |
| FR-002.5 | AC01-02, AGR-02/03/05, FND-10 |
| FR-002.6 | ELG-01..15, CFG-01..03 |
| FR-003.1 | AC02-01, REV-40..43 |
| FR-003.2 | REV-01..05 |
| FR-003.3 | REV-06..10 |
| FR-003.4 | AUD-02 |
| FR-003.5 | REV-30..33, REV-20 |
| FR-003.6 | SIS-05/06, SIS-14, REV-11..13 |
| FR-004.1 | AC01-02, AGR-01 |
| FR-004.2 | AGR-06 |
| FR-004.3 | AGR-02..05, AGR-20 |
| FR-005.1 | PAY-01..05, PAY-10/11 |
| FR-005.2 | PAY-20..26 |
| FR-005.3 | PAY-30..33 |
| FR-006.1 | AMT-01/02, ELG-08/09, REV-07..12 |
| FR-006.2 | PAY-20, FND-10 |
| FR-006.3 | ELG-11..15, PAY-40..44 |
| NFR-001.1 | FND-01/02 |
| NFR-001.2 | FND-04..06, AGR-13, PAY-32 |
| NFR-001.3 | FND-11, PAY-02/03 |
| NFR-001.4 | FND-10 |
| NFR-002.2 | SEC-01..05, APL-08, AGR-08/10, REV-15 |
| NFR-002.4 | PAY-25 |
| NFR-003.1–003.4 | AUD-01..09, CFG-01 |
| NFR-004.1–004.3 | AGR-07, AGR-09/10 |
| NFR-005.1 | PRF-01 |
| NFR-005.2 | SIS-01..06 |
| NFR-005.3 | AGR-11..13 |

## 5. Not tested in the prototype

These are deferred by architecture.md §5. They are listed so that nobody reads the coverage table as complete.

- NFR-002.1 (encryption at rest)
- NFR-002.3 (officer MFA)
- NFR-002.5 (FERPA/GLBA, quarterly reviews)
- NFR-004.1 legal compliance beyond the consent and intent fields
- NFR-004.4 (counsel approval)
- NFR-005.4 (99.9% availability)

---

## 6. Spec gaps

### 6.1 Requirements with no acceptance criterion

The ACs cover only parts of FR-001 and FR-002. These have no AC at all. The tests above were derived from the requirement text.

- **FR-001:** FR-001.2 (two SIS reads), FR-001.4 (SIS unavailable), FR-001.5, FR-001.6 (one active per term); FR-001.3's minimum and maximum limits (the ACs test only the gap limit).
- **FR-002:** FR-002.4 (appeals), FR-002.5 (reservation/release); FR-002.6's Fund availability and No overdue loans rules, and SAP "Warning".
- **FR-003:** all of FR-003.1–003.6. AC02-01 touches only the dashboard showing the triggering rule.
- **FR-004:** all of FR-004.1–004.3. AC01-02 only says "prompted to sign".
- **FR-005 and FR-006:** all of FR-005.1–005.3 and FR-006.1–006.3.
- **NFRs:** every NFR (NFR-001 to NFR-005).

### 6.2 Acceptance criteria with no requirement

- **SG-A1.** AC01-03: "my registration hold should remain in place". No requirement says the system ever changes a registration hold. FR-001.2 retrieves hold status, but no EligibilityRule uses it, and nothing defines what happens to the hold on approval or disbursement.
- **SG-A2.** AC01-01: "I should see a maximum loan amount of $600". FR-001.3 defines rejection limits, but no requirement says a maximum is displayed or how it is computed (architecture.md says min(gap, max)).
- **SG-A3.** AC01-04: "my eligibility assessment cannot reach a clear decision". No requirement uses this wording. It maps to "some rule returns Escalate" (FR-002.2) only by interpretation.
- **SG-A4.** AC02-01: "the Financial Aid Officer should see that the enrollment rule triggered the escalation". This matches the FR-03 user story, but no numbered FR-003.x requirement says the dashboard shows the triggering rule, gap or awards.

### 6.3 Ambiguities found while computing expected values (left unresolved)

| ID | Where | Question |
|---|---|---|
| SG-01 | FR-001.1 vs FR-001.3 | Gap is $0.01–$99.99: the student may start, but every amount fails either the min or the gap. Should they be told they cannot apply, or allowed to start with no valid amount? |
| SG-02 | FR-002.6 | SAP value other than Meeting/Warning/Suspended: Fail, Escalate, or "incomplete data" under FR-001.4? |
| SG-03 | FR-006.3 | Is an installment overdue on day 10 after the due date, or from day 11? Also, is "day" a calendar date or 24 h from a timestamp? |
| SG-04 | FR-003.6 | Must the SIS be reachable for an officer **denial**? |
| SG-05 | FR-001.6 | Is a denied application with a pending appeal "active"? |
| SG-06 | FR-002.4, FR-004.3 | Is "within 7 days" inclusive at exactly 7×24 h? |
| SG-07 | FR-003.2 | Does a whitespace-only rationale count as "entered"? |
| SG-08 | FR-003.3 vs FR-006.1 | Fund availability Fail cannot be overridden. If the fund can now cover the amount, may an officer approve the appeal, or must the student reapply? |
| SG-09 | FR-003.5 | Payment deadline is a date. When on that day does it expire, and in which time zone? |
| SG-10 | FR-003.1 | Tie-break order for reviews with the same deadline. |
| SG-11 | NFR-005.3 | Which calendar defines a "business day" (institutional holidays)? |
| SG-12 | FR-005.1 | How the base installment is rounded before adding the remainder. Truncation is assumed in PAY-02/03. |
| SG-13 | FR-005.1 | Installments 2–4: each +1 calendar month, or each +30 days? Also, what happens at month end? |
| SG-14 | FR-005.3 | No default value for reminder lead days. |
| SG-15 | FR-005.2 | Zero, negative, partial and over-payments: allowed? How are over-payments applied or refunded? |
| SG-16 | FR-005.2, NFR-002.2 | May anyone other than the borrower pay toward a loan? |
| SG-17 | FR-005.3 | Is a reminder sent for an installment already paid? |
| SG-18 | FR-006.3 | Where do flagged overdue Loans appear for the officer? FR-003.1's dashboard lists only ExceptionReviews. |
| SG-19 | FR-001.3, NFR-001.3 | Sub-cent amounts (e.g. 600.001): reject or round? |
| SG-20 | FR-002.6 | If configuration changes between start and submit, which version applies? Also, does a later threshold change affect an open review? |
| SG-21 | FR-002.5, FR-003.3 | An escalated application holds no reservation, so the fund can drain while it waits (REV-09). Is that intended? |
| SG-22 | FR-003.5, FR-002.4 | Applications or appeals submitted after the payment deadline would expire immediately. Should submission after the deadline be blocked? |
| SG-23 | FR-004.3 | No stated reason text for an application that expires unsigned (FR-003.5 gives one for review expiry). |
| SG-24 | FR-006.2 | "Originating loan fund" implies multiple funds; architecture.md supports one. Multi-fund crediting is untestable. |
| SG-25 | Errors and precedence | When a request is wrong in two ways (e.g. an active application exists **and** the gap is 0), which message is shown? Single-fault tests avoid this. |
