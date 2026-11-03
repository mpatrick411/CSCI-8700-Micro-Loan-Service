# Description
This project is a micro-loan service for bridging small university tuition gaps so students can stay on track toward their degrees when they face minor or last-minute funding shortfalls. If a student is missing some financial aid or scholarships are disbursed too late for university payment deadlines, they can apply for a small loan that the system evaluates automatically against specific eligibility rules and available loan fund balances. Students who are approved receive a loan agreement stating the amount and repayment terms. Once they sign it electronically, funds are disbursed internally directly toward the outstanding tuition balance. The system then manages repayment through schedules, one-time or automatic payments set by the student, and reminders, and it returns repaid funds to the originating loan fund. A Financial Aid Officer may oversee the process if flagged by the system for reviewing exceptions and following up on overdue loans, while the system keeps an automatic audit trail to support policy compliance and limit institutional default risk.

# Goals
1. **G-01** Funding gap covered
2. **G-02** Maintain degree progress
3. **G-03** Minimize institutional default risk
4. **G-04** Maintain institutional policy compliance
5. **G-05** Achieve complete audit trail

# Domain Model

## Actors
- Student
- Financial Aid Officer

## Objects
From my Project 1 submission Object Model:

- **DomainThing**
  - **AcademicEntity**
    - DegreeProgram
    - Enrollment
    - Term
  - **Event**
    - Decision
    - Disbursement
    - EligibilityAssessment
    - ExceptionReview
  - **FinancialEntity**
    - AidAward
    - Loan
    - LoanFund
    - Payment
    - RepaymentSchedule
    - TuitionCharge
  - **Policy**
    - EligibilityRule
  - **Record**
    - AuditRecord
    - LoanAgreement
    - LoanApplication
- **ValueThing**
  - ApplicationStatus
  - MonetaryAmount

# Functional Requirements
## FR 01: Submit a Loan Application
As a Student,
I want the application to calculate my tuition gap from my account balance and aid awards and let me submit a loan application for up to that amount,
So that my funding gap is covered without borrowing more money than I need.

- **FR-001.1:** The system shall calculate the tuition gap as the student's outstanding TuitionCharge balance for the current Term (charges minus payments and aid already posted) minus all AidAwards that are accepted but not yet disbursed. If the result is zero or negative, the student shall not be able to apply.
- **FR-001.2:** The system shall retrieve the student's TuitionCharge balance and AidAwards from the Student Information System (SIS) through a synchronous API call at the moment the application is started and again at submission.
- **FR-001.3:** The system shall reject a requested amount that is greater than the tuition gap, greater than the maximum loan amount (configurable, default $1,500), or less than the minimum loan amount (configurable, default $100).
- **FR-001.4:** If the SIS is unavailable or returns incomplete data, the system shall not allow submission and shall tell the student to try again later.
- **FR-001.5:** The SIS shall be the source of truth for tuition balances and aid awards. The system shall be the source of truth for loans, agreements, and loan payments.
- **FR-001.6:** A student shall have at most one active LoanApplication or Loan per Term. An application is active unless it has been denied or has expired; a Loan is active until it is fully repaid.
- **FR-001.7:** The SIS shall own registration holds. The system shall read a student's hold status but shall never change it; the SIS lifts the hold once the Disbursement posts to the student's tuition balance.
  
## FR 02: Receive an automated decision and disbursement
As a Student,
I want my application to be automatically checked against the university’s eligibility rules, provide an approval or denial for a stated reason, add approved funds directly to my tuition balance, and provide the necessary channels to escalate an appeal,
So that my tuition is covered quickly without waiting on manual processing.

- **FR-002.1:** The system shall evaluate every submitted application against each EligibilityRule and assign each rule one of three outcomes: Pass, Fail, or Escalate.
- **FR-002.2:** The system shall decide the application as follows: if any rule returns Fail, the application is denied; otherwise, if any rule returns Escalate, the application is escalated to a FinancialAidOfficer; otherwise, the application is approved.
- **FR-002.3:** A denial shall state every rule that returned Fail, in plain language.
- **FR-002.4:** A denied student shall be able to submit one appeal within 7 days (configurable) of the decision. An appeal creates an ExceptionReview and routes the application to a FinancialAidOfficer. An appeal does not re-run the EligibilityRules.
- **FR-002.5:** When an application is approved, the system shall reserve the requested amount from the LoanFund until the LoanAgreement is signed or the application expires (see FR-004.3).
**FR-002.6:** The system shall apply the following EligibilityRules. Thresholds shall be configurable, and each EligibilityAssessment shall record the rule-set version in effect.
+  - **Enrollment:** Pass at 6 or more credits for the Term; Escalate at 3–5 credits; Fail below 3 credits.
+  - **Satisfactory Academic Progress (SAP):** Pass if "Meeting"; Escalate if "Warning"; Fail if "Suspended".
+  - **Fund availability:** Pass if the LoanFund's available balance covers the requested amount; otherwise Fail. This rule never returns Escalate.
+  - **No overdue loans:** Pass if the student has no Loan with an overdue payment (see FR-006.3); otherwise Fail.

## FR 03: Review and override edge cases
As a Financial Aid Officer,
I want a dashboard showing escalated applications showing the student’s tuition gap, current awards, and the eligibility rule triggering the escalation, allowing me to approve or deny each one manually with a recorded rationale,
So that edge-case holds are resolved in time and institutional fairness is upheld.

- **FR-003.1:** The dashboard shall list every open ExceptionReview, whether it came from an escalation or an appeal, sorted by the student's tuition payment deadline, earliest first.
- **FR-003.2:** An officer shall not be able to approve or deny without entering a rationale.
- **FR-003.3:** An officer may override a Fail or Escalate outcome on any rule except Fund availability. An officer shall not approve a loan the LoanFund cannot cover (see FR-006.1).
- **FR-003.4:** Every manual decision shall create an AuditRecord containing the officer, timestamp, decision, rationale, and the rule outcomes at the time of the decision.
- **FR-003.5:** An ExceptionReview that is not resolved by the student's tuition payment deadline for the Term shall expire, and the application shall be denied with the reason "Review not completed before the payment deadline."

## FR-004: Loan Acceptance
- **FR-004.1:** The system shall generate a loan agreement containing the loan amount and repayment terms for every approved applicant.
- **FR-004.2:** The system shall not disburse funds until the student has electronically signed the loan agreement.
- **FR-004.3:** The system shall expire an approved application if the agreement is not signed within a set number of days, and release any reserved funds for the loan plan.

## FR-005: Repayment
- **FR-005.1:** The system shall create a RepaymentSchedule for each loan when the loan is issued: 0% interest, no fees, and 4 equal monthly installments (configurable), with the first due 30 days after Disbursement. Any remainder cents shall be added to the final installment.
- **FR-005.2:** The system shall allow students to make one-time payments or enroll in automatic payment plans, similarly to tuition payments.
- **FR-005.3:** The system shall send the student a reminder a configurable number of days before each payment is due.

## FR-006: Fund and Risk Management
- **FR-006.1:** The system shall not approve a loan whose amount exceeds the available balance of its loan fund or the student's tuition gap.
- **FR-006.2:** The system shall credit each student's payment back to the origination loan fund.
- **FR-006.3:** The system shall mark a payment overdue when it is 10 days (configurable) past its due date, and shall flag the Loan for FinancialAidOfficer follow-up.

# Acceptance Criteria

## AC-01 Submit a Loan Application
```gherkin
Feature: Apply for a tuition microloan
  As a Student,
  I want the system to calculate my tuition gap from my charges and aid awards
  and let me submit a loan application for up to that amount,
  So that my funding gap is covered without borrowing more than I need.

  Background:
    Given I am logged in as a Student
    And I have an outstanding tuition balance of $4,000 for the Fall 2026 term
    And I have accepted, undisbursed aid awards totaling $3,400 for the Fall 2026 term

  Scenario: Student sees their calculated tuition gap
    When I start a loan application for the Fall 2026 term
    Then I should see a tuition gap of $600
    And I should see a maximum loan amount of $600

  Scenario: Eligible student is automatically approved
    Given I have started a loan application for the Fall 2026 term
    When I request a loan of $600
    And I submit my application
    Then the eligibility assessment should determine I am eligible
    And I should see that my application is approved
    And I should be prompted to review and sign my loan agreement

  Scenario: Ineligible student is automatically denied
    Given I have started a loan application for the Fall 2026 term
    And I do not meet the eligibility rules for the Fall 2026 term
    When I request a loan of $600
    And I submit my application
    Then the eligibility assessment should determine I am not eligible
    And I should see that my application is denied
    And I should see the reason for the denial
    And my registration hold should remain in place

  Scenario: Edge-case application is escalated for manual review
    Given I have started a loan application for the Fall 2026 term
    And my eligibility assessment cannot reach a clear decision
    When I submit my application
    Then my application should be escalated to a Financial Aid Officer
    And I should see that my application is under review

  Scenario: Student cannot request more than their tuition gap
    Given I have started a loan application for the Fall 2026 term
    When I request a loan of $900
    Then I should see a message that the amount exceeds my tuition gap of $600
    And I should not be able to submit my application
```

## AC-02 Automated Loan Eligibility Decisions
```gherkin
Feature: Automated eligibility decision
  As a Student,
  I want my application to be automatically checked against the university's eligibility rules
  and receive an approval, denial, or escalation,
  So that my tuition is covered quickly without waiting on manual processing.

  Background:
    Given I am logged in as a Student
    And I have an outstanding tuition balance of $4,000 for the Fall 2026 term
    And I have accepted, undisbursed aid awards totaling $3,400 for the Fall 2026 term
    And I have started a loan application for the Fall 2026 term
    And I have requested a loan of $600
    And the loan fund has an available balance of at least $600

  Scenario: Part-time enrollment is escalated for manual review
    Given I am enrolled in 4 credits for the Fall 2026 term
    And my SAP status is "Meeting"
    When I submit my application
    Then my application should be escalated to a Financial Aid Officer
    And the Financial Aid Officer should see that the enrollment rule triggered the escalation

  Scenario: A failed rule takes priority over an escalation
    Given I am enrolled in 4 credits for the Fall 2026 term
    And my SAP status is "Suspended"
    When I submit my application
    Then my application should be denied

  Scenario: Denial lists every failed eligibility rule
    Given I am enrolled in 2 credits for the Fall 2026 term
    And my SAP status is "Suspended"
    When I submit my application
    Then my application should be denied
    And I should see that I do not meet the enrollment requirement
    And I should see that I do not meet the satisfactory academic progress requirement
```

# Nonfunctional Requirements

## NFR-01: Financial Transaction Integrity
- **NFR-001.1:** The system shall perform the LoanFund balance check and the fund reservation (FR-002.5) as a single atomic operation, so that concurrent approvals can never together exceed the available balance.
- **NFR-001.2:** The system shall make every money-moving operation (reservation, release, Disbursement, Payment crediting) idempotent, so that a retried request never creates a duplicate effect.
- **NFR-001.3:** The system shall represent every MonetaryAmount using exact decimal arithmetic, never floating point.
- **NFR-001.4:** At all times, each LoanFund balance shall equal its initial capital minus active reservations minus disbursed principal plus repaid principal, with zero unexplained discrepancy.

## NFR-02: Security and Privacy
- **NFR-002.1:** The system shall encrypt all student and financial data in transit and at rest.
- **NFR-002.2:** The system shall enforce role-based access: a Student may view only their own records; a FinancialAidOfficer may view only the records needed to perform their role.
- **NFR-002.3:** The system shall require multi-factor authentication for FinancialAidOfficer accounts.
- **NFR-002.4:** The system shall not store card or bank account numbers; payment details shall be tokenized by a PCI DSS–compliant payment processor.
- **NFR-002.5:** The system shall handle student data in accordance with FERPA and the GLBA Safeguards Rule, and access permissions shall be reviewed quarterly.

## NFR-03: Complete, Tamper-Evident Audit Trail
- **NFR-003.1:** The system shall create an AuditRecord for every state change, including automated and manual Decisions, EligibilityRule outcomes, fund reservations and releases, signatures, Disbursements, Payments, and configuration changes.
- **NFR-003.2:** Each AuditRecord shall contain the actor (system or user), timestamp, prior state, new state, and the EligibilityRule version in effect.
- **NFR-003.3:** AuditRecords shall be append-only; no application role shall be able to edit or delete them.
- **NFR-003.4:** Any Decision shall be reproducible from the AuditRecords alone.

## NFR-04: Legal Enforceability of Loan Agreements
- **NFR-004.1:** The system shall capture electronic signatures in compliance with ESIGN and UETA, including the student's consent to transact electronically and their intent to sign.
- **NFR-004.2:** The system shall store each signed LoanAgreement unaltered, with a document hash, signature timestamp, and consent record.
- **NFR-004.3:** The student shall be able to download their signed LoanAgreement at any time during the life of the loan.
- **NFR-004.4:** The content of the LoanAgreement and any required lending disclosures shall be approved by institutional counsel before launch.

## NFR-05: Timeliness and Availability
- **NFR-005.1:** The system shall display an eligibility Decision within 5 seconds of submission for 95% of applications.
- **NFR-005.2:** Each synchronous SIS call (FR-001.2) shall time out after 3 seconds and be handled as described in FR-001.4.
- **NFR-005.3:** The system shall post a Disbursement to the student's SIS tuition balance within 1 business day of the LoanAgreement being signed.
- **NFR-005.4:** The system shall be available 99.9% of the time during the 3 weeks before each Term's tuition payment deadline.
