# RecoverAI — Synthetic Scenario Specification

This document defines the canonical specification for the eight synthetic revenue recovery scenario archetypes implemented in **Phase 2**.

---

## 1. Scenario Taxonomy Overview

Each scenario represents a specific failure pattern and context designed to evaluate future recovery detection (Phase 3), AI root-cause diagnosis (Phase 4), and recovery decisioning (Phase 5).

| Scenario ID | Name | Default Weight (bps) | Target Type | Ground Truth (`is_recoverable`) |
|---|---|---|---|---|
| `high_probability_recoverable` | High Probability Recoverable Failure | 2000 (20%) | Payment | `True` |
| `low_probability_recoverable` | Low Probability Recoverable Failure | 1500 (15%) | Payment | `True` |
| `clearly_non_recoverable` | Clearly Non-Recoverable Failure | 1500 (15%) | Payment | `False` |
| `new_customer` | New Customer Failure | 1000 (10%) | Payment | `True` |
| `repeated_failure` | Repeated Failure Scenario | 1000 (10%) | Payment | `False` |
| `temporary_failure_after_success_history` | Temporary Failure with Strong History | 1500 (15%) | Payment | `True` |
| `subscription_failure` | Subscription Recurring Payment Failure | 1000 (10%) | Subscription | `True` |
| `high_value_payment_failure` | High-Value Transaction Failure | 500 (5%) | Payment | `True` |

*Note: Total default weights sum to 10,000 basis points (100%).*

---

## 2. Canonical Scenario Archetypes

### 2.1 `high_probability_recoverable`
* **Scenario ID:** `high_probability_recoverable`
* **Description:** A payment failure on a customer account where the failure cause is transient (e.g. transient gateway glitch or momentary timeout) and historical behavior shows high completion intent.
* **Observable Signals:**
  - `failure_code`: `temporary_failure` or `generic_decline`
  - `attempt_number`: 1 or 2
  - Prior customer transactions: Mix of successful payments present.
* **Applicable Customer Profiles:** `Reliable Customer`, `Intermittent Customer`, `High-Value Customer`.
* **Payment / Attempt Conditions:** Target payment status is `FAILED` with 1-2 attempts.
* **Ground-Truth Label:** `is_recoverable = True`
* **Expected Recovery Reason:** "Transient network or issuer glitch with high customer intent and historical reliability."
* **Target Type:** Payment

---

### 2.2 `low_probability_recoverable`
* **Scenario ID:** `low_probability_recoverable`
* **Description:** A payment failure where recovery is possible but less certain (e.g., expired payment method on an intermittent user who may need a reminder or alternate payment method).
* **Observable Signals:**
  - `failure_code`: `expired_payment_method` or `insufficient_funds`
  - `attempt_number`: 1
  - Prior customer transactions: Intermittent success history.
* **Applicable Customer Profiles:** `Intermittent Customer`, `Reliable Customer`.
* **Payment / Attempt Conditions:** Target payment status is `FAILED` with 1 attempt.
* **Ground-Truth Label:** `is_recoverable = True`
* **Expected Recovery Reason:** "Expired payment method or temporary balance deficit requiring customer intervention."
* **Target Type:** Payment

---

### 2.3 `clearly_non_recoverable`
* **Scenario ID:** `clearly_non_recoverable`
* **Description:** A payment failure resulting from hard decline, invalid payment instrument, or explicit customer abandonment with zero recovery signals.
* **Observable Signals:**
  - `failure_code`: `generic_decline` or `unknown_failure`
  - `attempt_number`: 1 or 2
  - Prior customer transactions: Low engagement or persistent prior declines.
* **Applicable Customer Profiles:** `Chronic Failure Customer`, `Intermittent Customer`.
* **Payment / Attempt Conditions:** Target payment status is `FAILED`.
* **Ground-Truth Label:** `is_recoverable = False`
* **Expected Recovery Reason:** "Hard card decline / invalid instrument with absence of alternative payment methods."
* **Target Type:** Payment

---

### 2.4 `new_customer`
* **Scenario ID:** `new_customer`
* **Description:** A first-time customer experiencing a failure on their first or second transaction.
* **Observable Signals:**
  - `failure_code`: `insufficient_funds` or `temporary_failure`
  - Prior customer transactions: 0 historical completed payments.
* **Applicable Customer Profiles:** `New Customer`.
* **Payment / Attempt Conditions:** Initial payment attempt failed.
* **Ground-Truth Label:** `is_recoverable = True`
* **Expected Recovery Reason:** "First-time customer checkout drop-off recoverable via checkout link or alternate payment method."
* **Target Type:** Payment

---

### 2.5 `repeated_failure`
* **Scenario ID:** `repeated_failure`
* **Description:** Multiple consecutive failed attempts for the same transaction indicating persistent issuer block or insolvency.
* **Observable Signals:**
  - `failure_code`: `insufficient_funds` or `generic_decline`
  - `attempt_number`: >= 3 consecutive failed attempts on the same payment.
* **Applicable Customer Profiles:** `Chronic Failure Customer`, `Intermittent Customer`, `Reliable Customer`.
* **Payment / Attempt Conditions:** Target payment status is `FAILED` with >= 3 failed attempts.
* **Ground-Truth Label:** `is_recoverable = False`
* **Expected Recovery Reason:** "Exhausted repeated attempts with persistent issuer refusal."
* **Target Type:** Payment

---

### 2.6 `temporary_failure_after_success_history`
* **Scenario ID:** `temporary_failure_after_success_history`
* **Description:** A highly reliable customer with a long sequence of successful historical payments suddenly encounters a temporary payment failure.
* **Observable Signals:**
  - `failure_code`: `temporary_failure`
  - Prior customer transactions: >= 3 successful historical payments with >= 85% success rate.
  - `attempt_number`: 1
* **Applicable Customer Profiles:** `Reliable Customer`, `High-Value Customer`.
* **Payment / Attempt Conditions:** Target payment status is `FAILED` with 1 attempt.
* **Ground-Truth Label:** `is_recoverable = True`
* **Expected Recovery Reason:** "Strong historical payment track record affected by transient technical failure."
* **Target Type:** Payment

---

### 2.7 `subscription_failure`
* **Scenario ID:** `subscription_failure`
* **Description:** A recurring subscription billing attempt fails due to temporary insufficient funds or mandate processing glitch.
* **Observable Signals:**
  - Target entity: `Subscription` with status `PAST_DUE`.
  - `interval`: `monthly` or `yearly`.
* **Applicable Customer Profiles:** `Reliable Customer`, `Intermittent Customer`, `High-Value Customer`.
* **Payment / Attempt Conditions:** Subscription status transitioned to `PAST_DUE`.
* **Ground-Truth Label:** `is_recoverable = True`
* **Expected Recovery Reason:** "Recurring billing failure recoverable via smart retry schedule or update payment link."
* **Target Type:** Subscription

---

### 2.8 `high_value_payment_failure`
* **Scenario ID:** `high_value_payment_failure`
* **Description:** A high-ticket payment (>= ₹5,000 / 500,000 paise) fails, representing significant revenue at risk with high merchant recovery value.
* **Observable Signals:**
  - `amount_minor`: >= 500,000 paise (>= ₹5,000).
  - `failure_code`: `temporary_failure` or `insufficient_funds`.
* **Applicable Customer Profiles:** `High-Value Customer`.
* **Payment / Attempt Conditions:** High-value payment status `FAILED`.
* **Ground-Truth Label:** `is_recoverable = True`
* **Expected Recovery Reason:** "High-value order failure with strong customer intent justifying high-priority recovery intervention."
* **Target Type:** Payment

---

## 3. Strict Architectural Boundary

Ground truth metadata (`is_recoverable`, `scenario_type`, `expected_recovery_reason`) is generated solely for evaluation purposes. It is stored in the evaluation layer (`RecoveryGroundTruth` records) and is **never** included in observable transaction payloads, database tables, or inputs to AI reasoning engines.
