# Description

# Goals

# Domain Model

## Actors
Student
Financial Aid Officer

## Objects


# Functional Requirements
## FR 01: Submit a Loan Application
As a Student,
I want the application to calculate my tuition gap from my account balance and aid awards and let me submit a loan application for up to that amount,
So that my funding gap is covered without borrowing more money than I need.

## FR 02: Receive an automated decision and disbursement
As a Student,
I want my application to be automatically checked against the university’s eligibility rules, provide an approval or denial for a stated reason, add approved funds directly to my tuition balance, and provide the necessary channels to escalate an appeal,
So that my tuition is covered quickly without waiting on manual processing.

## FR 03: Review and override edge cases
As a Financial Aid Officer,
I want a dashboard showing escalated applications showing the student’s tuition gap, current awards, and the eligibility rule triggering the escalation, allowing me to approve or deny each one manually with a recorded rationale,
So that edge-case holds are resolved in time and institutional fairness is upheld.

# Acceptance Criteria

## Submit a Loan Application
```gherkin
Feature: Apply for a tuition microloan
  As a Student,
  I want the system to calculate my tuition gap from my charges and aid awards
  and let me submit a loan application for up to that amount,
  So that my funding gap is covered without borrowing more than I need.

  Background:
    Given I am logged in as a Student
    And I have a tuition charge of $4,000 for the Fall 2026 term
    And I have aid awards totaling $3,400 for the Fall 2026 term

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
