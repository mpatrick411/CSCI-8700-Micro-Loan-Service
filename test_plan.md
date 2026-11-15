# Test Plan: Tuition Gap Micro-Loan Service

Sources: `spec.md` (primary) and `architecture.md` (used only where spec.md does not decide an expected value; those cases are marked **[arch]**).

All expected values were worked out by hand from the requirements. This plan does not depend on any implementation code.

---

## 0. Conventions

### 0.1 Baseline fixture (applies to every test unless the test overrides it)

| Item | Value |
|---|---|
| Clock (frozen, injectable) | 2026-09-01 09:00:00, institution local time. All times in this plan are institution local time. |
| Term | Fall 2026. Payment deadline **2026-09-15** (lasts until the end of that date). |
| Students | S1, S2, S3: all with the same SIS data unless overridden |
| SIS data per student (Fall 2026) | Outstanding TuitionCharge balance (net of posted payments and aid) **$4,000.00**; one AidAward, accepted and not yet disbursed, **$3,400.00**; Enrollment **12 credits**; SAP **"Meeting"**; no registration hold; payment deadline 2026-09-15 |
| Derived tuition gap | $4,000.00 − $3,400.00 = **$600.00** (FR-001.1) |
| Max requestable | min($600.00, $1,500.00) = **$600.00** (FR-001.3) |
| Officers | O1, O2 (role FinancialAidOfficer) |
| LoanFund | F1, initial capital **$10,000.00**, no entries. Available $10,000.00, reserved $0.00, disbursed $0.00, repaid $0.00 |
| Config version **v1** (defaults) | min loan $100.00; max loan $1,500.00; appeal window 7 days; signing window 7 days; 4 installments, 30 days apart; reminder lead 3 days; overdue after 10 days; Enrollment Pass ≥ 6, Escalate 3–5, Fail < 3; SAP Meeting = Pass, Warning = Escalate, Suspended = Fail |
| Existing records | No applications, loans or reviews |
| Mock SIS | Up, latency 0 s, complete data |

Fund state is written as **F1 = available / reserved / disbursed / repaid**.

### 0.2 Standard checks

- **NC (nothing created).** After a rejected request: no new LoanApplication, EligibilityAssessment, ExceptionReview, LoanAgreement, Loan, RepaymentSchedule, Payment, Disbursement or ledger entry. F1 balances are unchanged, the SIS has received no posting, and any existing record keeps its previous status.
- **NM (no money moved).** After a denial (a decision, not a rejected request): the LoanApplication and its EligibilityAssessment are stored as *denied*, but there is no ledger entry, LoanAgreement, Loan or ExceptionReview, and F1 is unchanged.

### 0.3 Kinds

- **AC**: refinement of an acceptance criterion.
- **inside / outside**: the case just inside or just outside a limit.
- **control**: an accepted request with the same shape as a rejection, so the rejection can only come from the requirement under test.
- **extra**: added from the gap checklist. The *Probes* column names the requirement it tests.

Every rejection names its control in the **Pair** column.

---

## 1. AC-01: Submit a Loan Application (refined)

```gherkin
Feature: Apply for a tuition microloan
  Background:
    Given the baseline fixture (§0.1)
    And I am logged in as Student S1
    And my SIS outstanding tuition balance for Fall 2026 is $4,000.00
    And my accepted, undisbursed AidAwards for Fall 2026 total $3,400.00

  @TP-AC01-01 @AC @FR-001.1 @FR-001.3 @FR-001.6
  Scenario: Student sees their calculated tuition gap
    When I start a loan application for Fall 2026
    Then I see a tuition gap of $600.00
    And I see a maximum requestable amount of $600.00
    And the number of LoanApplications for S1 is 0

  @TP-AC01-02 @AC @FR-002.1 @FR-002.2 @FR-002.5 @FR-004.1
  Scenario: Eligible student is automatically approved
    Given I have started a loan application for Fall 2026
    When I request $600.00
    And I submit at 2026-09-01 09:00:00
    Then the EligibilityAssessment records Enrollment=Pass, SAP=Pass, Fund availability=Pass, No overdue loans=Pass, rule-set version v1
    And the application status is approved
    And a LoanAgreement exists with amount $600.00 and status pending_signature
    And F1 = $9,400.00 / $600.00 / $0.00 / $0.00
    And I am prompted to review and sign the LoanAgreement

  @TP-AC01-03 @AC @FR-002.2 @FR-002.3 @FR-002.6
  Scenario: Ineligible student is automatically denied
    Given I am enrolled in 2 credits for Fall 2026
    And I have started a loan application for Fall 2026
    When I request $600.00
    And I submit
    Then the EligibilityAssessment records Enrollment=Fail, SAP=Pass, Fund availability=Pass, No overdue loans=Pass
    And the application status is denied
    And the denial reasons list exactly one rule: Enrollment
    And NM holds (F1 = $10,000.00 / $0.00 / $0.00 / $0.00)

  @TP-AC01-04 @AC @FR-002.2
  Scenario: Edge-case application is escalated for manual review
    Given my SAP status is "Warning" and I am enrolled in 12 credits
    And I have started a loan application for Fall 2026
    When I request $600.00
    And I submit
    Then the EligibilityAssessment records SAP=Escalate and every other rule Pass
    And exactly one open ExceptionReview (escalation) exists for the application
    And I see that my application is under review
    And no LoanAgreement exists
    And F1 = $10,000.00 / $0.00 / $0.00 / $0.00

  @TP-AC01-05 @AC @FR-001.3   # Pair: TP-AC01-02
  Scenario: Student cannot request more than their tuition gap
    Given I have started a loan application for Fall 2026
    When I request $900.00
    Then I see a message that the amount exceeds my tuition gap of $600.00
    And submit is disabled
    And NC holds
```

## 2. AC-02: Automated Loan Eligibility Decisions (refined)

```gherkin
Feature: Automated eligibility decision
  Background:
    Given the baseline fixture (§0.1)
    And I am logged in as Student S1 with gap $600.00
    And I have started a Fall 2026 application and requested $600.00
    And F1 available balance is $10,000.00

  @TP-AC02-01 @AC @FR-002.2 @FR-002.6 @FR-003.1
  Scenario: Part-time enrollment is escalated for manual review
    Given I am enrolled in 4 credits and my SAP status is "Meeting"
    When I submit
    Then the EligibilityAssessment records Enrollment=Escalate, SAP=Pass, Fund availability=Pass, No overdue loans=Pass
    And one open ExceptionReview (escalation) exists
    And officer O1's dashboard entry for this review shows gap $600.00, AidAward $3,400.00, and exactly one rule: Enrollment (Escalate)
    And F1 = $10,000.00 / $0.00 / $0.00 / $0.00

  @TP-AC02-02 @AC @FR-002.2 @FR-002.3
  Scenario: A failed rule takes priority over an escalation
    Given I am enrolled in 4 credits and my SAP status is "Suspended"
    When I submit
    Then the application is denied
    And the EligibilityAssessment records Enrollment=Escalate and SAP=Fail
    And the denial reasons list exactly one rule: SAP
    And no ExceptionReview exists
    And NM holds

  @TP-AC02-03 @AC @FR-002.3
  Scenario: Denial lists every failed eligibility rule
    Given I am enrolled in 2 credits and my SAP status is "Suspended"
    When I submit
    Then the application is denied
    And the denial reasons list exactly two rules: Enrollment and SAP, each in plain language
    And NM holds
```

---

## 3. Tuition gap and maximum requestable amount (FR-001.1, FR-001.3)

| ID | Kind | Probes | Given (beyond baseline) | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-GAP-01 | inside | FR-001.1 | Balance $3,500.00, aid $3,400.00 → gap $100.00 | S1 starts | Start allowed; shows gap $100.00 and max requestable $100.00 | — |
| TP-GAP-02 | outside | FR-001.1 | Balance $3,499.99, aid $3,400.00 → gap $99.99 | S1 starts | Start refused; NC | TP-GAP-01 |
| TP-GAP-03 | extra (boundaries) | FR-001.1 | Balance $3,000.00, aid $3,400.00 → gap −$400.00 | S1 starts | Start refused; NC | TP-GAP-01 |
| TP-GAP-04 | extra (input types) | FR-001.1 | Baseline, plus a second AidAward of $500.00 that is *offered, not accepted* | S1 starts | Gap shown $600.00 (unaccepted aid not subtracted) | — |
| TP-GAP-05 | extra (input types) | FR-001.1 | Two accepted, undisbursed awards: $2,000.00 and $1,400.00 | S1 starts | Gap shown $600.00 (all accepted awards summed) | — |
| TP-GAP-06 | extra (what is returned) | FR-001.3 | Balance $5,000.00 → gap $1,600.00 | S1 starts | Shows gap $1,600.00, max requestable $1,500.00 | — |
| TP-GAP-07 | inside | FR-001.3 | Balance $4,900.00 → gap $1,500.00 | S1 starts | Max requestable $1,500.00 | — |
| TP-GAP-08 | outside | FR-001.3 | Balance $4,900.01 → gap $1,500.01 | S1 starts | Max requestable $1,500.00 (cap applies) | — |
| TP-GAP-09 | inside | FR-001.3 | Balance $4,899.99 → gap $1,499.99 | S1 starts | Max requestable $1,499.99 (gap applies) | — |

## 4. Requested amount validation (FR-001.3)

Unless noted, gap = $600.00. "Accepted" means the request passes validation and submits; with baseline data it is then approved.

| ID | Kind | Probes | Given | When (request, submit) | Then | Pair |
|---|---|---|---|---|---|---|
| TP-AMT-01 | inside | FR-001.3 (≤ gap) | — | $600.00 | Accepted; approved; F1 = $9,400.00 / $600.00 / $0.00 / $0.00 | — |
| TP-AMT-02 | outside | FR-001.3 (≤ gap) | — | $600.01 | Rejected: exceeds gap of $600.00; submit disabled; NC | TP-AMT-01 |
| TP-AMT-03 | inside | FR-001.3 (≥ min) | — | $100.00 | Accepted; approved; F1 = $9,900.00 / $100.00 / $0.00 / $0.00 | — |
| TP-AMT-04 | outside | FR-001.3 (≥ min) | — | $99.99 | Rejected (below minimum); NC | TP-AMT-03 |
| TP-AMT-05 | inside | FR-001.3 (≤ max) | Balance $5,000.00 → gap $1,600.00 | $1,500.00 | Accepted; approved; F1 = $8,500.00 / $1,500.00 / $0.00 / $0.00 | — |
| TP-AMT-06 | outside | FR-001.3 (≤ max) | Balance $5,000.00 → gap $1,600.00 | $1,500.01 | Rejected (above maximum); NC | TP-AMT-05 |
| TP-AMT-07 | inside | FR-001.3 (≤ 2 dp) | — | $599.99 | Accepted; approved; reserved $599.99 | — |
| TP-AMT-08 | outside | FR-001.3 (≤ 2 dp) | — | $599.995 | Rejected (more than two decimal places); NC | TP-AMT-07 |
| TP-AMT-09 | extra (input types) | FR-001.3 | — | $600.0 (one decimal place) | Accepted as $600.00; reserved $600.00 | — |
| TP-AMT-10 | extra (input types) | FR-001.3 | — | $0.00 | Rejected (below minimum); NC | TP-AMT-03 |
| TP-AMT-11 | extra (input types) | FR-001.3 | — | −$100.00 | Rejected (below minimum); NC | TP-AMT-03 |
| TP-AMT-12 | extra (errors) | FR-001.3 server-side; [arch] step 6 | — | POST $900.00 straight to the submit endpoint, bypassing the UI | Rejected (exceeds gap); NC | TP-AMT-01 |
| TP-AMT-13 | extra (time/state) | FR-001.2 (re-read at submit), FR-001.3 | SIS returns balance $4,000.00 at start; balance $3,900.00 at submit → submit-time gap $500.00 | Start; request $600.00; submit | Rejected: exceeds gap of $500.00; NC | TP-AC01-02 |
| TP-AMT-14 | inside | FR-001.3 (configurable max) | Config v2: max $1,000.00, set before start; gap $1,600.00 | Start; request $1,000.00 | Max requestable shown $1,000.00; accepted; reserved $1,000.00 | — |
| TP-AMT-15 | outside | FR-001.3 (configurable max) | As TP-AMT-14 | Request $1,000.01 | Rejected (above maximum); NC | TP-AMT-14 |

## 5. SIS integration and failures (FR-001.2, FR-001.4, NFR-005.2)

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-SIS-01 | extra (errors) | FR-001.4 | Mock SIS outage | S1 starts | Start refused; "try again later" shown; NC | TP-AC01-01 |
| TP-SIS-02 | extra (errors) | FR-001.2, FR-001.4 | SIS up at start, outage at submit | Start; request $600.00; submit | Submit refused; "try again later"; NC | TP-AC01-02 |
| TP-SIS-03 | extra (input types) | FR-001.4 | SIS returns SAP "Probation" at submit | Request $600.00; submit | Submit refused; "try again later"; NC | TP-SIS-04 |
| TP-SIS-04 | control | FR-001.4 | SIS returns SAP "Warning" | Request $600.00; submit | Accepted; escalated (SAP=Escalate) | — |
| TP-SIS-05 | extra (input types) | FR-001.4 | SIS response is missing the Term payment deadline | Request $600.00; submit | Submit refused; "try again later"; NC | TP-AC01-02 |
| TP-SIS-06 | inside | NFR-005.2 | SIS latency 2.5 s on both calls | Start; request $600.00; submit | Accepted; approved | — |
| TP-SIS-07 | outside | NFR-005.2, FR-001.4 | SIS latency 3.5 s at submit | Request $600.00; submit | Submit refused; "try again later"; NC | TP-SIS-06 |
| TP-SIS-08 | extra (what is returned) | FR-001.2 | Baseline | Start; request $600.00; submit | The mock SIS logs exactly 2 read calls for S1 (one at start, one at submit) | — |

Note: TP-SIS-06/07 use 2.5 s and 3.5 s rather than 2.99 s and 3.01 s so that timer jitter cannot decide the outcome. See Spec gap G-19.

## 6. One active application or loan per term (FR-001.6)

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-ONE-01 | extra (state) | FR-001.6 (start creates nothing) | — | S1 starts, then leaves without submitting; S1 starts again | LoanApplications for S1 = 0 after the first start; second start allowed and shows gap $600.00 | — |
| TP-ONE-02 | extra (state) | FR-001.6; [arch] start check | S1 has A1 (Fall 2026, approved, pending_signature, $600.00) | S1 starts a Fall 2026 application | Start refused; NC (still 1 application; F1 reserved $600.00) | TP-ONE-06 |
| TP-ONE-03 | extra (state) | FR-001.6; [arch] unique index | As TP-ONE-02 | POST submit for Fall 2026 at $600.00 directly | Refused; NC | TP-ONE-06 |
| TP-ONE-04 | extra (state) | FR-001.6 | S1 has A1 escalated (open ExceptionReview) | S1 submits a second Fall 2026 application, $600.00 | Refused; NC | TP-ONE-06 |
| TP-ONE-05 | extra (state) | FR-001.6 ("under appeal is active") | S1 has A1 denied (2 credits) and appealed; SIS now reports 12 credits | S1 submits a second Fall 2026 application, $600.00 | Refused; NC | TP-ONE-06 |
| TP-ONE-06 | control | FR-001.6 (denied is not active) | S1 has A1 denied, not appealed; SIS now reports 12 credits | S1 submits a second Fall 2026 application, $600.00 | Accepted; approved; S1 has 2 applications (A1 denied, A2 approved) | — |
| TP-ONE-07 | control | FR-001.6 (expired is not active) | S1's A1 was approved at 2026-09-01 09:00:00 and expired unsigned (clock now 2026-09-08 09:00:01, expiry job run) | S1 submits a second Fall 2026 application, $600.00 | Accepted; approved; F1 = $9,400.00 / $600.00 / $0.00 / $0.00 | — |
| TP-ONE-08 | extra (state) | FR-001.6 (loan active until repaid) | S1 has a Fall 2026 Loan with $0.01 outstanding; mock SIS set to gap $600.00 | S1 submits a Fall 2026 application, $600.00 | Refused; NC | TP-ONE-09 |
| TP-ONE-09 | control | FR-001.6 | S1's Fall 2026 Loan is fully repaid ($0.00 outstanding); SIS gap $600.00 | S1 submits a Fall 2026 application, $600.00 | Accepted; approved | — |
| TP-ONE-10 | control | FR-001.6 (per Term) | S1 has A1 (Fall 2026, approved, pending_signature); Spring 2027 SIS data: balance $4,000.00, aid $3,400.00, 12 credits, Meeting, deadline 2027-01-15 | S1 submits a Spring 2027 application, $600.00 | Accepted; approved | — |
| TP-ONE-11 | extra (concurrency) | FR-001.6; NFR-001.1 | Baseline | S1 sends two Fall 2026 submits for $600.00 at the same time | Exactly 1 LoanApplication; exactly 1 reservation; F1 = $9,400.00 / $600.00 / $0.00 / $0.00; the other request is refused | — |

## 7. Eligibility rules and decision logic (FR-002.1–002.3, FR-002.6)

All requests are $600.00 and submitted at 2026-09-01 09:00:00 unless stated.

| ID | Kind | Probes | Given | Then | Pair |
|---|---|---|---|---|---|
| TP-RUL-01 | inside | FR-002.6 Enrollment Pass ≥ 6 | 6 credits | Enrollment=Pass; approved | — |
| TP-RUL-02 | outside | FR-002.6 Enrollment Pass ≥ 6 | 5 credits | Enrollment=Escalate; escalated; 1 open ExceptionReview; F1 unchanged | — |
| TP-RUL-03 | inside | FR-002.6 Enrollment Escalate ≥ 3 | 3 credits | Enrollment=Escalate; escalated | — |
| TP-RUL-04 | outside | FR-002.6 Enrollment Escalate ≥ 3 | 2 credits | Enrollment=Fail; denied; reasons [Enrollment]; NM (same as TP-AC01-03) | — |
| TP-RUL-05 | inside | FR-002.6 Fund availability | F1 initial capital $600.00 | Fund availability=Pass; approved; F1 = $0.00 / $600.00 / $0.00 / $0.00 | — |
| TP-RUL-06 | outside | FR-002.6 Fund availability | F1 initial capital $599.99 | Fund availability=Fail; denied; reasons [Fund availability]; NM (F1 = $599.99 / $0.00 / $0.00 / $0.00) | TP-RUL-05 |
| TP-RUL-07 | extra (state) | FR-002.6 Fund availability counts reservations | F1 initial $1,000.00; S2 already approved for $600.00 (F1 = $400.00 / $600.00 / $0.00 / $0.00) | S1: Fund availability=Fail; denied; F1 still $400.00 / $600.00 / $0.00 / $0.00 | TP-RUL-05 |
| TP-RUL-08 | extra (precedence) | FR-002.2 | 4 credits (Escalate) and F1 initial $599.99 (Fail) | Denied; reasons [Fund availability]; no ExceptionReview; NM | — |
| TP-RUL-09 | inside | FR-002.6 No overdue loans; FR-006.3 | S1 has a Spring 2026 Loan with an installment due 2026-08-20, unpaid. Clock 2026-08-30 09:00:00 (10 days after due date) | No overdue loans=Pass; approved | — |
| TP-RUL-10 | outside | FR-002.6 No overdue loans; FR-006.3 | Same loan; clock 2026-08-31 09:00:00 (11 days after due date) | No overdue loans=Fail; denied; reasons [No overdue loans]; NM | TP-RUL-09 |
| TP-RUL-11 | extra (time) | FR-006.3; [arch] computed from Clock at assessment | As TP-RUL-10, but the overdue-flag job has **not** run | No overdue loans=Fail; denied | TP-RUL-09 |
| TP-RUL-12 | extra (listing) | FR-003.1 | 4 credits and SAP "Warning" | Escalated; dashboard entry lists exactly Enrollment (Escalate) and SAP (Escalate) | — |

## 8. Rule-set and limit versioning (FR-002.6, NFR-003.1)

| ID | Kind | Probes | Given | When | Then |
|---|---|---|---|---|---|
| TP-VER-01 | extra (time/state) | FR-002.6 | S1 (4 credits) submitted under v1 → escalated | Admin changes Enrollment Pass threshold to ≥ 4 (creates v2) | Open review still shows Enrollment=Escalate; the stored assessment's version is v1; no new EligibilityAssessment exists |
| TP-VER-02 | control | FR-002.6 | After the TP-VER-01 change (v2 in effect) | S2 (4 credits) submits $600.00 | Enrollment=Pass; approved; assessment version v2 |
| TP-VER-03 | extra (time/state) | FR-002.6 (loan limits at submission) | S1 gap $1,600.00 (balance $5,000.00), SAP "Warning"; submits $1,200.00 under v1 → escalated; then max loan changed to $1,000.00 (v2) | O1 approves with rationale "OK" at 2026-09-02 10:00:00 | Approved; F1 = $8,800.00 / $1,200.00 / $0.00 / $0.00 |
| TP-VER-04 | extra (what is returned) | NFR-003.1, NFR-003.2 | — | Admin changes max loan from $1,500.00 to $1,000.00 | One new AuditRecord with actor = the admin, timestamp, prior value $1,500.00, new value $1,000.00 |

## 9. Appeals (FR-002.4)

Fixture A1: S1 with 2 credits submits $600.00 at 2026-09-01 09:00:00 and is denied (decision timestamp 2026-09-01 09:00:00). The appeal window ends at 2026-09-08 09:00:00 (168 h).

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-APL-01 | inside | FR-002.4 window | A1 | S1 appeals at 2026-09-08 09:00:00 with explanation "Adding 4 credits next week" | Accepted; one ExceptionReview (appeal) open with the explanation; A1 is under appeal (active); review shows Enrollment=Fail from the original assessment; no new EligibilityAssessment; F1 unchanged | — |
| TP-APL-02 | outside | FR-002.4 window | A1 | S1 appeals at 2026-09-08 09:00:01 | Refused; NC; A1 stays denied | TP-APL-01 |
| TP-APL-03 | extra (input types) | FR-002.4 (explanation optional) | A1 | S1 appeals at 2026-09-02 09:00:00 with no explanation | Accepted; ExceptionReview (appeal) open | — |
| TP-APL-04 | extra (state) | FR-002.4 (one appeal) | A1 appealed on 2026-09-02; O1 denied the appeal with rationale "No change" | S1 appeals A1 again at 2026-09-03 09:00:00 | Refused; NC; A1 stays denied | TP-APL-01 |
| TP-APL-05 | extra (state) | FR-002.4 (one appeal) | A1 appealed on 2026-09-02; that review still open | S1 appeals A1 again at 2026-09-03 09:00:00 | Refused; NC; still exactly 1 ExceptionReview | TP-APL-01 |
| TP-APL-06 | extra (state) | FR-002.4 (refused if another active) | A1, plus S1's A2 (Fall 2026, approved 2026-09-02, pending_signature) | S1 appeals A1 at 2026-09-03 09:00:00 | Refused; NC | TP-APL-07 |
| TP-APL-07 | control | FR-002.4 | A1, plus S1's A2 (Fall 2026) also denied | S1 appeals A1 at 2026-09-03 09:00:00 | Accepted; ExceptionReview (appeal) open | — |
| TP-APL-08 | extra (state) | FR-002.4 (no re-run) | A1; SIS now reports 12 credits | S1 appeals at 2026-09-02 09:00:00 | Review shows Enrollment=Fail (original); count of EligibilityAssessments for A1 = 1 | — |
| TP-APL-09 | extra (identity) | FR-002.4; NFR-002.2 | A1 belongs to S1 | S2 appeals A1 at 2026-09-02 09:00:00 | Refused; NC | TP-APL-01 |
| TP-APL-10 | extra (time) | FR-002.4 + FR-003.5 | A1 appealed at 2026-09-05 09:00:00; not resolved | Clock moves to 2026-09-16 00:00:00; expiry job runs | Review expired; A1 denied with reason "Review not completed before the payment deadline."; F1 unchanged | — |

## 10. Officer review (FR-003)

Fixture E1: S1 with 4 credits submits $600.00 at 2026-09-01 09:00:00 → escalated, review R1 opened 2026-09-01 09:00:00.
Fixture P1: S1 with 2 credits and SAP "Suspended" submits $600.00 at 2026-09-01 09:00:00 → denied; S1 appeals at 2026-09-01 10:00:00 → review R2.

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-OFF-01 | extra (listing) | FR-003.1 sort order | Open reviews: Ra (S1, deadline 2026-09-20, opened 2026-09-01 09:00, escalation); Rb (S2, deadline 2026-09-15, opened 2026-09-01 11:00, escalation); Rc (S3, deadline 2026-09-15, opened 2026-09-01 10:00, appeal); Rd (resolved) | O1 opens the dashboard | Order is exactly Rc, Rb, Ra; Rd not listed | — |
| TP-OFF-02 | extra (what is returned) | FR-003.1 | P1/R2 | O1 opens the dashboard | R2 entry shows gap $600.00, AidAward $3,400.00, Enrollment=Fail, SAP=Fail; Fund availability and No overdue loans not listed | — |
| TP-OFF-03 | extra (identity) | NFR-002.2; FR-003.1 | E1 | S1 requests the dashboard | Refused; no review data returned | TP-OFF-01 |
| TP-OFF-04 | extra (input types) | FR-003.2 | E1 | O1 approves R1 with rationale "" | Refused; R1 open; NC | TP-OFF-07 |
| TP-OFF-05 | extra (input types) | FR-003.2 | E1 | O1 approves R1 with rationale "   " (3 spaces) | Refused; R1 open; NC | TP-OFF-07 |
| TP-OFF-06 | extra (input types) | FR-003.2 | E1 | O1 approves R1 with rationale "\t\n " | Refused; R1 open; NC | TP-OFF-07 |
| TP-OFF-07 | control | FR-003.2, FR-003.4, FR-002.5 | E1 | O1 approves R1 at 2026-09-02 10:00:00 with rationale "x" | Approved; R1 resolved; LoanAgreement pending_signature, $600.00; F1 = $9,400.00 / $600.00 / $0.00 / $0.00; AuditRecord: actor O1, timestamp 2026-09-02 10:00:00, decision approve, rationale "x", rule outcomes Enrollment=Escalate, SAP=Pass, Fund availability=Pass, No overdue loans=Pass | — |
| TP-OFF-08 | extra (input types) | FR-003.2 (deny) | E1 | O1 denies R1 with rationale "" | Refused; R1 open; NC | TP-OFF-09 |
| TP-OFF-09 | control | FR-003.2, FR-003.4 | E1 | O1 denies R1 at 2026-09-02 10:00:00 with rationale "Below enrollment minimum" | Denied; R1 resolved; NM; AuditRecord with actor O1, decision deny, that rationale, and the four rule outcomes | — |
| TP-OFF-10 | extra (state) | FR-003.3 (override Fail) | P1/R2 | O1 approves R2 at 2026-09-02 10:00:00 with rationale "SAP appeal granted" | Approved; F1 = $9,400.00 / $600.00 / $0.00 / $0.00 | — |
| TP-OFF-11 | extra (state) | FR-003.3 (Fund re-checked, not overridden) | F1 initial $1,000.00; S2 approved $600.00 at 08:00 (available $400.00); S1 submits $600.00 at 09:00 → denied (Fund=Fail); S1 appeals at 09:30 (R3); S2's application expires unsigned, releasing $600.00 (available $1,000.00) | O1 approves R3 with rationale "Funds now available" | Approved; F1 = $400.00 / $600.00 / … | — |
| TP-OFF-12 | inside | FR-003.3, FR-006.1 | F1 initial $1,200.00; E1 (escalated; no reservation); then S2 approved $600.00 → F1 available $600.00 | O1 approves R1 with rationale "x" | Approved; F1 available $0.00, reserved $1,200.00 | — |
| TP-OFF-13 | outside | FR-003.3, FR-006.1 | F1 initial $1,199.99; E1; then S2 approved $600.00 → F1 available $599.99 | O1 approves R1 with rationale "x" | Refused; R1 open; NC (F1 available $599.99) | TP-OFF-12 |
| TP-OFF-14 | outside | FR-003.6, FR-006.1 (gap) | E1; at approval the SIS returns balance $3,999.99 → gap $599.99 | O1 approves R1 with rationale "x" | Refused; R1 open; NC | TP-OFF-07 (SIS gap $600.00 = inside) |
| TP-OFF-15 | control | FR-003.6 (deny still allowed) | As TP-OFF-14 | O1 denies R1 with rationale "Gap shrank" | Denied; NM | — |
| TP-OFF-16 | extra (errors) | FR-003.6 | E1; mock SIS outage | O1 approves R1 with rationale "x" | Refused; "try again later"; R1 open; NC | TP-OFF-07 |
| TP-OFF-17 | extra (errors) | FR-003.6 (deny needs no SIS) | E1; mock SIS outage | O1 denies R1 with rationale "x" | Denied; NM; SIS read count during deny = 0 | — |
| TP-OFF-18 | inside | FR-003.5; Time conventions | E1; clock 2026-09-15 23:59:59 | O1 approves R1 with rationale "x" | Approved; reservation $600.00 | — |
| TP-OFF-19 | outside | FR-003.5; [arch] checked at moment of action | E1; clock 2026-09-16 00:00:00; expiry job **not** run | O1 approves R1 with rationale "x" | Refused; NC (no reservation, no agreement) | TP-OFF-18 |
| TP-OFF-20 | extra (time) | FR-003.5 | E1; clock 2026-09-16 00:00:00 | Expiry job runs | R1 expired; E1 denied with reason "Review not completed before the payment deadline."; AuditRecord actor = system; F1 unchanged | — |
| TP-OFF-21 | extra (time) | FR-003.5 | E1; clock 2026-09-15 23:59:59 | Expiry job runs | R1 still open; E1 still escalated | — |
| TP-OFF-22 | extra (concurrency) | FR-003; [arch] compare-and-set | E1 | O1 and O2 approve R1 at the same time, rationale "x" | Exactly one approval recorded; one reservation of $600.00 (F1 = $9,400.00 / $600.00 / …); one approval AuditRecord; the other request is refused | — |
| TP-OFF-23 | extra (identity) | NFR-002.2 | E1 | S1 calls the approve endpoint for R1 with rationale "x" | Refused; R1 open; NC | TP-OFF-07 |

## 11. Loan agreement and signing (FR-004, FR-002.5, NFR-004)

Fixture G1: S1 approved for $600.00 at 2026-09-01 09:00:00 (TP-AC01-02). The signing window ends at 2026-09-08 09:00:00.

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-AGR-01 | extra (what is returned) | FR-004.1, FR-005.1 | G1 | S1 views the agreement | Shows amount $600.00, 0% interest, no fees, 4 installments of $150.00, due 30 days apart, first due 30 days after the disbursement posts | — |
| TP-AGR-02 | extra (state) | FR-004.2 | G1, unsigned | Disbursement-posting job runs at 2026-09-02 10:00:00 | No Disbursement; SIS posting count 0; F1 = $9,400.00 / $600.00 / $0.00 / $0.00 | — |
| TP-AGR-03 | inside | FR-004.3, FR-002.5, FR-005.1, NFR-004.2 | G1 | S1 signs at 2026-09-08 09:00:00 | Signed; F1 = $9,400.00 / $0.00 / $600.00 / $0.00; Loan with 4 installments of $150.00 and no due dates yet [arch]; Disbursement $600.00 pending; signature record has consent, intent, timestamp 2026-09-08 09:00:00 and a SHA-256 hash | — |
| TP-AGR-04 | outside | FR-004.3 | G1 | S1 signs at 2026-09-08 09:00:01 | Refused; NC (no Loan, no Disbursement) | TP-AGR-03 |
| TP-AGR-05 | extra (time) | FR-004.3 | G1; clock 2026-09-08 09:00:01 | Expiry job runs | Application expired; F1 = $10,000.00 / $0.00 / $0.00 / $0.00 | — |
| TP-AGR-06 | inside | FR-004.3; Time conventions | G1; clock 2026-09-08 09:00:00 | Expiry job runs | Application still pending_signature; F1 reserved $600.00 | — |
| TP-AGR-07 | extra (concurrency) | FR-004.3; [arch] compare-and-set | G1. S1's sign request passes its signing-window check at 2026-09-08 08:59:59. The expiry job runs at 2026-09-08 09:00:01, before the sign request commits | Both complete | Exactly one outcome: either signed (F1 = $9,400.00 / $0.00 / $600.00 / $0.00, one Loan, one pending Disbursement) or expired (F1 = $10,000.00 / $0.00 / $0.00 / $0.00, no Loan, no Disbursement). Never both, never neither | — |
| TP-AGR-08 | extra (identity) | NFR-002.2 | G1 | S2 signs S1's agreement | Refused; NC | TP-AGR-03 |
| TP-AGR-09 | extra (state) | NFR-001.2 | G1 signed at 2026-09-02 09:00:00 | S1 submits the sign request again | Second request does not create a second Loan, Disbursement or ledger entry; F1 = $9,400.00 / $0.00 / $600.00 / $0.00 | — |
| TP-AGR-10 | inside | FR-004.3 (officer path) | TP-OFF-07 approval at 2026-09-02 10:00:00 | S1 signs at 2026-09-09 10:00:00 | Signed | — |
| TP-AGR-11 | outside | FR-004.3 (officer path) | As TP-AGR-10 | S1 signs at 2026-09-09 10:00:01 | Refused; NC | TP-AGR-10 |
| TP-AGR-12 | extra (what is returned) | NFR-004.3, NFR-004.2 | G1 signed; clock 2026-12-31 | S1 downloads the signed agreement | Download succeeds; SHA-256 of the bytes equals the stored hash | — |
| TP-AGR-13 | extra (identity) | NFR-002.2 | As TP-AGR-12 | S2 downloads S1's agreement | Refused; no bytes returned | TP-AGR-12 |

## 12. Disbursement and repayment schedule (FR-005.1, NFR-005.3, NFR-001.2)

Fixture D1: G1 signed at 2026-09-02 09:00:00.

| ID | Kind | Probes | Given | When | Then |
|---|---|---|---|---|---|
| TP-DIS-01 | extra (time) | FR-005.1 | D1 | Posting job succeeds at 2026-09-02 10:00:00 | SIS receives one credit of $600.00 keyed by the Disbursement ID; posted_at 2026-09-02 10:00:00; due dates 2026-10-02, 2026-11-01, 2026-12-01, 2026-12-31 |
| TP-DIS-02 | extra (concurrency) | NFR-001.2 | After TP-DIS-01 | Posting is retried with the same idempotency key | SIS credit count for the Disbursement = 1; due dates unchanged |
| TP-DIS-03 | extra (errors) | [arch] retry pending postings | D1; mock SIS outage at 2026-09-02 10:00:00 | Posting job runs; SIS recovers; job runs again at 2026-09-02 11:00:00 | After the first run the Disbursement is pending and has no due dates. After the second run: one SIS credit of $600.00, posted_at 2026-09-02 11:00:00, due dates 2026-10-02, 2026-11-01, 2026-12-01, 2026-12-31 |
| TP-DIS-04 | extra (time) | FR-005.1; Time conventions | D1 | Posting succeeds at 2026-09-02 23:30:00 local (already 2026-09-03 in UTC if the institution is west of UTC) | First due date 2026-10-02 (counted from the local date) |

| ID | Kind | Probes | Loan amount | Expected installments (sum) |
|---|---|---|---|---|
| TP-SCH-01 | extra (boundaries) | FR-005.1 rounding | $600.00 | $150.00, $150.00, $150.00, $150.00 ($600.00) |
| TP-SCH-02 | extra (boundaries) | FR-005.1 remainder | $100.01 | $25.00, $25.00, $25.00, $25.01 ($100.01) |
| TP-SCH-03 | extra (boundaries) | FR-005.1 remainder | $599.99 | $149.99, $149.99, $149.99, $150.02 ($599.99) |
| TP-SCH-04 | extra (boundaries) | FR-005.1 largest remainder | $100.03 | $25.00, $25.00, $25.00, $25.03 ($100.03) |
| TP-SCH-05 | extra (boundaries) | FR-005.1 at max | $1,500.00 | $375.00 ×4 ($1,500.00) |
| TP-SCH-06 | extra (state) | FR-005.1 configurable count | $100.00, with config v2 (3 installments) set **before** submission; posted 2026-09-02 | $33.33, $33.33, $33.34 ($100.00); due 2026-10-02, 2026-11-01, 2026-12-01 |

## 13. Payments (FR-005.2, FR-006.2, NFR-001)

Fixture L1: TP-DIS-01 complete. Loan $600.00; installments of $150.00 due 2026-10-02, 2026-11-01, 2026-12-01, 2026-12-31. F1 = $9,400.00 / $0.00 / $600.00 / $0.00. Clock 2026-09-10 09:00:00.

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-PAY-01 | extra (state) | FR-005.2 ordering; FR-006.2 | L1 | S1 pays $200.00 | Inst1 paid ($150.00); inst2 has $50.00 applied, $100.00 remaining; outstanding $400.00; F1 = $9,600.00 / $0.00 / $600.00 / $200.00 | — |
| TP-PAY-02 | inside | FR-005.2 (≤ outstanding) | L1 | S1 pays $600.00 | Accepted; all installments paid; outstanding $0.00; Loan no longer active; F1 = $10,000.00 / $0.00 / $600.00 / $600.00 | — |
| TP-PAY-03 | outside | FR-005.2 (≤ outstanding) | L1 | S1 pays $600.01 | Refused; NC | TP-PAY-02 |
| TP-PAY-04 | inside | FR-005.2 (> $0.00) | L1 | S1 pays $0.01 | Accepted; inst1 remaining $149.99; outstanding $599.99; F1 repaid $0.01 | — |
| TP-PAY-05 | outside | FR-005.2 (> $0.00) | L1 | S1 pays $0.00 | Refused; NC | TP-PAY-04 |
| TP-PAY-06 | extra (input types) | FR-005.2 | L1 | S1 pays −$50.00 | Refused; NC | TP-PAY-04 |
| TP-PAY-07 | inside | FR-005.2 after a partial payment | After TP-PAY-01 (outstanding $400.00) | S1 pays $400.00 | Accepted; outstanding $0.00; F1 = $10,000.00 / $0.00 / $600.00 / $600.00 | — |
| TP-PAY-08 | outside | FR-005.2 after a partial payment | After TP-PAY-01 | S1 pays $400.01 | Refused; NC (outstanding stays $400.00) | TP-PAY-07 |
| TP-PAY-09 | extra (identity) | FR-005.2 (own loans only) | L1 belongs to S1 | S2 pays $200.00 toward L1 | Refused; NC | TP-PAY-01 |
| TP-PAY-10 | extra (state) | FR-005.2 | L1 fully repaid (after TP-PAY-02) | S1 pays $0.01 | Refused (exceeds outstanding $0.00); NC | TP-PAY-04 |
| TP-PAY-11 | extra (boundaries) | NFR-001.3 | L1 | S1 pays $0.10, then $0.20 | Outstanding exactly $599.70; inst1 remaining exactly $149.70; F1 repaid exactly $0.30 | — |
| TP-PAY-12 | extra (concurrency) | NFR-001.2 | L1 | A $200.00 payment is submitted twice with the same idempotency key | One Payment; outstanding $400.00; F1 repaid $200.00 | — |
| TP-PAY-13 | extra (what is stored) | NFR-002.4 | L1 | S1 pays $150.00 with mock card 4242 4242 4242 4242; separately enrols in autopay with the same card | Database contains only token IDs; no column in any table contains "4242424242424242" | — |

## 14. Reminders (FR-005.3)

Fixture: L1, no payments made. The reminder job runs once on each date tested.

| ID | Kind | Probes | Given | When (job date) | Then |
|---|---|---|---|---|---|
| TP-REM-01 | inside | FR-005.3 lead days | L1 | 2026-09-29 | Exactly one reminder to S1 for inst1 (due 2026-10-02) in the notifications outbox |
| TP-REM-02 | outside | FR-005.3 lead days | L1 | 2026-09-28 | No reminder for inst1 |
| TP-REM-03 | control | FR-005.3 ("unpaid") | L1; S1 paid $150.00 on 2026-09-20 (inst1 fully paid) | 2026-09-29 | No reminder for inst1 |
| TP-REM-04 | extra (time) | FR-005.3 later installments | L1 | 2026-10-29 | One reminder for inst2 (due 2026-11-01) |
| TP-REM-05 | inside | FR-005.3 configurable | L1; reminder lead set to 5 (v2) | 2026-09-27 | One reminder for inst1 |
| TP-REM-06 | outside | FR-005.3 configurable | As TP-REM-05 | 2026-09-26 | No reminder for inst1 |

## 15. Overdue marking and follow-up list (FR-006.3)

Fixture: L1, inst1 due 2026-10-02, unpaid.

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-OVD-01 | inside | FR-006.3 | L1 | Overdue job runs 2026-10-12 (10 days after) | Inst1 not overdue; L1 not on the follow-up list | — |
| TP-OVD-02 | outside | FR-006.3 | L1 | Overdue job runs 2026-10-13 (11 days after) | Inst1 overdue; L1 on the follow-up list shown to O1 | — |
| TP-OVD-03 | control | FR-006.3 ("remains unpaid") | L1; inst1 paid in full on 2026-10-05 | Overdue job runs 2026-10-13 | Inst1 not overdue; L1 not on the list | — |
| TP-OVD-04 | inside | FR-006.3 configurable | L1; overdue days set to 5 (v2) | Job runs 2026-10-07 | Not overdue | — |
| TP-OVD-05 | outside | FR-006.3 configurable | As TP-OVD-04 | Job runs 2026-10-08 | Overdue; L1 on the list | — |
| TP-OVD-06 | extra (identity) | NFR-002.2 | After TP-OVD-02 | S1 requests the follow-up list | Refused; no list data returned | TP-OVD-02 |

## 16. Ledger and fund integrity (FR-002.5, FR-006.2, NFR-001)

| ID | Kind | Probes | Steps | Expected F1 after each step (available / reserved / disbursed / repaid) |
|---|---|---|---|---|
| TP-LED-01 | extra (state) | NFR-001.4 | (a) baseline; (b) S1 approved $600.00; (c) S1 signs; (d) posting; (e) S1 pays $150.00 | (a) 10,000.00 / 0.00 / 0.00 / 0.00; (b) 9,400.00 / 600.00 / 0.00 / 0.00; (c) 9,400.00 / 0.00 / 600.00 / 0.00; (d) unchanged; (e) 9,550.00 / 0.00 / 600.00 / 150.00. At every step, available = 10,000.00 − reserved − disbursed + repaid |
| TP-LED-02 | extra (state) | FR-002.5, FR-004.3 | (a) S1 approved $600.00; (b) expires unsigned at 2026-09-08 09:00:01 | (a) 9,400.00 / 600.00 / 0.00 / 0.00; (b) 10,000.00 / 0.00 / 0.00 / 0.00 |
| TP-LED-03 | extra (concurrency) | NFR-001.1 | F1 initial $1,000.00; S1 and S2 (both otherwise eligible) submit $600.00 at the same time | One approved, one denied with Fund availability=Fail; F1 = 400.00 / 600.00 / 0.00 / 0.00; available never below 0.00 |
| TP-LED-04 | extra (concurrency) | NFR-001.2 | After TP-LED-02, the expiry job runs again (same release) | One release entry; F1 = 10,000.00 / 0.00 / 0.00 / 0.00 (not 10,600.00) |

## 17. Audit trail (FR-003.4, NFR-003)

| ID | Kind | Probes | Given | When | Then |
|---|---|---|---|---|---|
| TP-AUD-01 | extra (what is returned) | NFR-003.1, NFR-003.2 | — | TP-AC01-02 runs | AuditRecords exist for: application created, 4 rule outcomes, decision approved, reservation $600.00. Each has a non-empty actor, timestamp 2026-09-01 09:00:00, prior state, new state and rule version v1. The decision record's actor = system |
| TP-AUD-02 | extra (errors) | NFR-003.3 | Any AuditRecord | The app's DB session issues UPDATE, then DELETE, on it | Both rejected; the record is unchanged |
| TP-AUD-03 | extra (errors) | NFR-03 (tamper-evident); [arch] hash chain | 10 AuditRecords; record #5's new-state field edited outside the app with triggers dropped | Chain verification runs | Reports the first broken link at record #5. Control: the same chain without the edit verifies OK |
| TP-AUD-04 | extra (what is returned) | NFR-003.4 | TP-AC01-02, TP-AC01-03, TP-AC01-04 completed | Rebuild each decision from AuditRecords alone (stored snapshot + version v1) | Approved, denied [Enrollment], escalated: identical to the stored decisions |
| TP-AUD-05 | extra (state) | NFR-003.1; [arch] advance-time endpoint | — | Admin advances the clock from 2026-09-01 09:00:00 to 2026-09-08 09:00:01 | One AuditRecord with prior 2026-09-01 09:00:00 and new 2026-09-08 09:00:01 |
| TP-AUD-06 | extra (errors) | NFR-003.1; [arch] same transaction | Fault injected after the reservation write, before commit, during TP-AC01-02 | Submit | Transaction rolls back: no LoanApplication, no ledger entry, no AuditRecord for this request; F1 = 10,000.00 / 0.00 / 0.00 / 0.00 |

## 18. Identity (NFR-002.2)

| ID | Kind | Probes | Given | When | Then | Pair |
|---|---|---|---|---|---|---|
| TP-SEC-01 | extra (identity) | NFR-002.2 | S1 has application A1 | S2 requests A1 | Refused; no A1 data in the response | TP-SEC-02 |
| TP-SEC-02 | control | NFR-002.2 | S1 has application A1 | S1 requests A1 | Returned | — |
| TP-SEC-03 | extra (identity) | NFR-002.2; [arch] student_id from resolved user | Logged in as S1 | S1 submits $600.00 with `student_id=S2` in the request body | Application created for S1; S2 has 0 applications | — |

## 19. Timeliness (NFR-005.1)

| ID | Kind | Probes | Given | When | Then |
|---|---|---|---|---|---|
| TP-PERF-01 | extra (time) | NFR-005.1 | 200 distinct eligible students; F1 initial $200,000.00; mock SIS latency 0 s | Each submits $600.00, sequentially | At least 190 of 200 decisions are displayed within 5 s of submission |

---

## 20. Coverage cross-check

| Gap-checklist category | Tests |
|---|---|
| Boundaries | GAP, AMT, RUL, SCH, PAY, OVD, REM |
| Time | APL-01/02/10, OFF-18–21, AGR-03–06/10/11, DIS-04, RUL-09–11, VER |
| Identity | APL-09, OFF-03/23, AGR-08/13, PAY-09, OVD-06, SEC |
| State | ONE, APL-04–08, AGR-09, PAY-10, LED |
| Concurrency | ONE-11, OFF-22, AGR-07, LED-03/04, DIS-02, PAY-12 |
| Input types | AMT-08–11, SIS-03/05, OFF-04–06, PAY-06, GAP-04/05 |
| Errors and precedence | SIS, OFF-16/17, DIS-03, AUD-02/03/06, AC02-02, RUL-08 |
| Listing | OFF-01/02, RUL-12, OVD-02 |
| What is returned | AC01-01, GAP-06–09, AGR-01/12, OFF-02/07, AUD-01/04 |

Not tested because the architecture explicitly defers them for the prototype: NFR-002.1 (encryption), NFR-002.3 (MFA), NFR-002.5 (FERPA/GLBA process), NFR-004.1 legal compliance beyond capturing consent and intent, NFR-004.4 (counsel approval), NFR-005.4 (availability).

---

## 21. Spec gaps

### 21.1 Requirements with no acceptance criterion

AC-01 and AC-02 cover only parts of FR-001.1, FR-001.3, FR-002.1–002.3, FR-002.6 (Enrollment and SAP only), and the escalation line of FR-003.1. These have **no** acceptance criterion:

- FR-001.1 (the "gap below the minimum" clause), FR-001.2, FR-001.4, FR-001.5, FR-001.6
- FR-001.3 limits other than "exceeds gap": maximum, minimum, decimal places
- FR-002.4 (appeals), FR-002.5 (reservation)
- FR-002.6: Fund availability and No overdue loans rules, the SAP "Warning" outcome, versioning
- FR-003.1 sort order; FR-003.2, FR-003.3, FR-003.4, FR-003.5, FR-003.6 (no AC for the officer at all)
- FR-004.1–004.3, FR-005.1–005.3, FR-006.1–006.3
- All NFRs (NFR-001 to NFR-005)

### 21.2 Acceptance criteria with no requirement

- **AC-01 "Eligible student is automatically approved", "I should be prompted to review and sign my loan agreement".** FR-004.1 requires generating the agreement, but no FR requires prompting the student.
- **AC-01 "Edge-case application is escalated", "I should see that my application is under review".** No FR requires telling the student that an application is escalated, or names the status shown.
- **AC-01 "Student cannot request more than their tuition gap": the message text** "the amount exceeds my tuition gap of $600". FR-001.3 requires rejection but no message. The wording of the other rejection messages (min, max, decimals) is defined nowhere, so tests TP-AMT-04/06/08 assert rejection only.
- **AC-01 "Student sees their calculated tuition gap", "maximum loan amount of $600".** In FR-001.3, "maximum loan amount" is the configurable cap ($1,500); the value displayed is the "maximum requestable amount". The AC uses the cap's name for the displayed value.

### 21.3 Expected values neither document determines (tests left out)

| # | Question | Requirement |
|---|---|---|
| G-01 | What happens with a non-numeric or empty amount ("abc", "")? FR-001.3 lists rejection reasons but no rule for non-numbers. | FR-001.3 |
| G-02 | Does "600.000" (trailing zeros past two places) count as "more than two decimal places"? | FR-001.3 |
| G-03 | How are fractional enrollment credits (such as 5.5) classified? The bands are stated as whole numbers (6+, 3–5, < 3). | FR-002.6 |
| G-04 | Registration hold status is retrieved, but no EligibilityRule uses it. Does a hold affect the decision? Is an unrecognised hold value "incomplete data"? | FR-001.2, FR-001.4, FR-002.6 |
| G-05 | Are payment amounts with more than two decimal places rejected? | FR-005.2 |
| G-06 | Is a partially paid installment "unpaid" for reminders and for overdue marking? | FR-005.3, FR-006.3 |
| G-07 | Once an overdue installment is paid, is it still "overdue"? Does the Loan leave the follow-up list, and does the "No overdue loans" rule then return Pass? | FR-006.3, FR-002.6 |
| G-08 | When and for how much does autopay charge (on the due date? the installment amount? the remaining balance)? | FR-005.2 |
| G-09 | Can a student appeal a denial made by an officer, or a denial from review expiry? Can they appeal an approved application that expired unsigned? FR-002.4 says only "a denied student". | FR-002.4, FR-003.5, FR-004.3 |
| G-10 | Is an appeal allowed inside the 7-day window but after the Term payment deadline? Its ExceptionReview would already be past the expiry point. | FR-002.4, FR-003.5 |
| G-11 | Can a student start or submit an application after the Term payment deadline? If escalated then, does the review expire at once? | FR-001, FR-003.5 |
| G-12 | Is the dashboard's tuition gap the value at submission or a fresh SIS read? (Tests keep SIS data unchanged so either reading gives the same result.) | FR-003.1 |
| G-13 | Do the "rule outcomes at the time of the decision" in an officer's AuditRecord include the Fund availability re-check result, or only the original assessment? | FR-003.4, FR-003.3 |
| G-14 | Which config version sets installment count and spacing: the one at submission or the one at signing? (TP-SCH-06 sets it before submission to avoid this.) | FR-005.1, FR-002.6 |
| G-15 | What exactly does "within 1 business day" mean: by the same clock time on the next business day, or by the end of the next business day? | NFR-005.3 |
| G-16 | If the reminder job runs twice on the same day, is a second reminder sent? At what time of day is a reminder due? | FR-005.3 |
| G-17 | What is the institution's time zone? Tests express all times in local time, which works for any zone, but the fixture needs a value. | Time Conventions |
| G-18 | Can an agreement be signed after the Term payment deadline if the 7-day signing window is still open? | FR-004.3 |
| G-19 | Does an SIS response at exactly 3.000 s time out or succeed? | NFR-005.2 |
| G-20 | Can an officer deny an escalated review after the payment deadline but before the expiry job has run? | FR-003.5 |
| G-21 | Should a rejected request (such as a failed validation) create an AuditRecord? NFR-003.1 covers state changes only, so the NC check does not assert either way. | NFR-003.1 |
| G-22 | What does the system do with a request that carries no user identity? The architecture uses mock identity only. | NFR-002.2 |
| G-23 | Can a student make a payment after signing but before the Disbursement posts, when due dates are not yet set? | FR-005.1, FR-005.2 |
