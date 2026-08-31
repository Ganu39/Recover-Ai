# RecoverAI — Data Model Documentation

This document outlines the foundational PostgreSQL data model designed in **Phase 1** for RecoverAI, an AI Revenue Recovery platform for the Razorpay AI Buildathon.

---

## 1. Entity Overview

The Phase 1 schema defines five core business entities:

1. **`Customer` (`customers`)**: Represents a merchant's end customer.
2. **`Payment` (`payments`)**: Represents the logical payment/order amount a customer is attempting to pay.
3. **`PaymentAttempt` (`payment_attempts`)**: Represents an individual attempt (e.g. gateway transaction) associated with a logical `Payment`.
4. **`Subscription` (`subscriptions`)**: Represents an ongoing, recurring payment relationship.
5. **`RecoveryCase` (`recovery_cases`)**: Represents a potential revenue recovery opportunity identified from a failed payment or subscription.

---

## 2. Entity Relationships (ERD)

```text
┌─────────────────┐
│    Customer     │
│─────────────────│
│ id (PK, UUID)   │
│ external_cust_id│◄─────────────┐
│ email           │              │
└────────┬────────┘              │
         │ 1:N                   │ 1:N
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│     Payment     │    │  Subscription   │
│─────────────────│    │─────────────────│
│ id (PK, UUID)   │    │ id (PK, UUID)   │
│ customer_id (FK)│    │ customer_id (FK)│
│ amount_minor    │    │ amount_minor    │
│ status          │    │ status          │
└────────┬────────┘    └────────┬────────┘
         │ 1:N                  │
         ▼                      │
┌─────────────────┐             │
│ PaymentAttempt  │             │
│─────────────────│             │
│ id (PK, UUID)   │             │
│ payment_id (FK) │             │
│ attempt_number  │             │
│ status          │             │
└─────────────────┘             │
         │                      │
         │ 1:N (Nullable)       │ 1:N (Nullable)
         └──────────┬───────────┘
                    ▼
          ┌───────────────────────────┐
          │       RecoveryCase        │
          │───────────────────────────│
          │ id (PK, UUID)             │
          │ payment_id (FK, Nullable) │
          │ subscription_id (FK, Null)│
          │ status                    │
          │ amount_at_risk_minor      │
          │ [Target Exactly-One CHECK]│
          └───────────────────────────┘
```

---

## 3. Field Descriptions & Types

### 3.1 `customers`
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid.uuid4()` | Unique internal identifier. |
| `external_customer_id` | `VARCHAR(255)` | Unique, Indexed, Not Null | Merchant / gateway customer identifier. |
| `email` | `VARCHAR(255)` | Indexed, Not Null | Customer email address. |
| `name` | `VARCHAR(255)` | Nullable | Customer display name. |
| `created_at` | `TIMESTAMPTZ` | Not Null, Server Default `now()` | Timestamp of record creation. |
| `updated_at` | `TIMESTAMPTZ` | Not Null, Server Default `now()` | Timestamp of last record modification. |

### 3.2 `payments`
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid.uuid4()` | Unique internal identifier. |
| `external_payment_id` | `VARCHAR(255)` | Unique, Indexed, Not Null | Merchant / gateway order/payment ID. |
| `customer_id` | `UUID` | FK `customers.id` (RESTRICT), Indexed, Not Null | Customer who initiated the payment. |
| `amount_minor` | `BIGINT` | Not Null, `CHECK (amount_minor >= 0)` | Monetary amount in integer minor units (paise/cents). |
| `currency` | `VARCHAR(3)` | Not Null | ISO 4217 3-letter currency code (e.g. `INR`, `USD`). |
| `status` | `VARCHAR(50)` | Indexed, Not Null, Enum CHECK | Logical payment state. |
| `created_at` | `TIMESTAMPTZ` | Indexed, Not Null, Server Default `now()` | Creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | Not Null, Server Default `now()` | Last modification timestamp. |

### 3.3 `payment_attempts`
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid.uuid4()` | Unique attempt identifier. |
| `payment_id` | `UUID` | FK `payments.id` (CASCADE), Indexed, Not Null | Associated parent Payment. |
| `attempt_number` | `INTEGER` | Not Null, `CHECK (attempt_number > 0)` | Monotonically increasing attempt sequence (1, 2, ...). |
| `status` | `VARCHAR(50)` | Not Null, Enum CHECK | Attempt result (`INITIATED`, `SUCCESSFUL`, `FAILED`). |
| `failure_code` | `VARCHAR(100)` | Nullable | Generic failure category / code (e.g. `CARD_DECLINED`, `EXPIRED_CARD`). |
| `failure_reason` | `TEXT` | Nullable | Detailed failure description or error message. |
| `attempted_at` | `TIMESTAMPTZ` | Indexed, Not Null, Server Default `now()` | Timestamp when the attempt was submitted. |

### 3.4 `subscriptions`
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid.uuid4()` | Unique subscription identifier. |
| `external_subscription_id` | `VARCHAR(255)` | Unique, Indexed, Not Null | External subscription reference. |
| `customer_id` | `UUID` | FK `customers.id` (RESTRICT), Indexed, Not Null | Associated customer. |
| `amount_minor` | `BIGINT` | Not Null, `CHECK (amount_minor >= 0)` | Recurring billing amount in minor units. |
| `currency` | `VARCHAR(3)` | Not Null | ISO 4217 3-letter currency code. |
| `status` | `VARCHAR(50)` | Indexed, Not Null, Enum CHECK | Subscription lifecycle status. |
| `interval` | `VARCHAR(50)` | Not Null | Recurring frequency (`monthly`, `yearly`, `weekly`, `daily`). |
| `created_at` | `TIMESTAMPTZ` | Not Null, Server Default `now()` | Creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | Not Null, Server Default `now()` | Last update timestamp. |

### 3.5 `recovery_cases`
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid.uuid4()` | Unique recovery opportunity identifier. |
| `payment_id` | `UUID` | FK `payments.id` (SET NULL), Indexed, Nullable | Target Payment (if recovering a failed one-off payment). |
| `subscription_id` | `UUID` | FK `subscriptions.id` (SET NULL), Indexed, Nullable | Target Subscription (if recovering a failed recurring cycle). |
| `status` | `VARCHAR(50)` | Indexed, Not Null, Enum CHECK | Recovery lifecycle state. |
| `amount_at_risk_minor` | `BIGINT` | Not Null, `CHECK (amount_at_risk_minor >= 0)` | Total revenue at risk in minor units. |
| `currency` | `VARCHAR(3)` | Not Null | ISO 4217 currency code. |
| `detected_at` | `TIMESTAMPTZ` | Indexed, Not Null, Server Default `now()` | When the recovery opportunity was detected. |
| `resolved_at` | `TIMESTAMPTZ` | Nullable | When the recovery case reached a terminal state. |

---

## 4. Money Representation & Safety

Fintech applications must never use floating-point types (`FLOAT`, `DOUBLE`, `REAL`) for monetary representation due to decimal round-off errors and binary approximation inaccuracies.

* **Database Type:** `BIGINT` (64-bit integer)
* **Unit:** Minor currency units (e.g., paise for INR, cents for USD).
* **Examples:**
  * ₹499.00 = `49900`
  * ₹1,250.50 = `125050`
* **Constraint:** Database-level `CHECK (amount_minor >= 0)` and `CHECK (amount_at_risk_minor >= 0)` prevent negative money balances.

---

## 5. Status Values & State Machine

Status columns use controlled string enumerations enforced at the database level via CHECK constraints:

### `PaymentStatus`
* `CREATED`: Payment intent initialized.
* `AUTHORIZED`: Payment authorized by issuer.
* `CAPTURED`: Funds successfully captured.
* `FAILED`: Payment failure occurred.
* `REFUNDED`: Payment refunded.

### `PaymentAttemptStatus`
* `INITIATED`: Attempt dispatched to gateway.
* `SUCCESSFUL`: Attempt succeeded.
* `FAILED`: Attempt declined or failed.

### `SubscriptionStatus`
* `ACTIVE`: Subscription active and in good standing.
* `PAST_DUE`: Recurring charge failed; grace period active.
* `CANCELLED`: Subscription cancelled.
* `HALTED`: Subscription suspended due to unrecovered failure.

### `RecoveryCaseStatus`
* `DETECTED`: Revenue risk opportunity flagged.
* `EVALUATING`: Root-cause diagnosis in progress.
* `ACTION_PENDING`: Recovery action proposed / awaiting safety clearance.
* `RECOVERED`: Lost revenue successfully collected.
* `UNRECOVERABLE`: Exhausted allowed recovery attempts.
* `CLOSED`: Case closed / abandoned.

---

## 6. Constraints

1. **Primary Keys:** UUID primary keys (`pk_<table_name>`) on all tables.
2. **Unique Identifiers:**
   * `uq_customers_external_customer_id`
   * `uq_payments_external_payment_id`
   * `uq_subscriptions_external_subscription_id`
3. **Foreign Keys:**
   * `payments.customer_id` → `customers.id` (ON DELETE RESTRICT)
   * `subscriptions.customer_id` → `customers.id` (ON DELETE RESTRICT)
   * `payment_attempts.payment_id` → `payments.id` (ON DELETE CASCADE)
   * `recovery_cases.payment_id` → `payments.id` (ON DELETE SET NULL)
   * `recovery_cases.subscription_id` → `subscriptions.id` (ON DELETE SET NULL)
4. **Monetary Safety Constraints:**
   * `ck_payments_ck_payment_amount_non_negative`: `CHECK (amount_minor >= 0)`
   * `ck_subscriptions_ck_subscription_amount_non_negative`: `CHECK (amount_minor >= 0)`
   * `ck_recovery_cases_ck_recovery_case_amount_non_negative`: `CHECK (amount_at_risk_minor >= 0)`
5. **Positive Attempt Numbers:**
   * `ck_payment_attempts_ck_payment_attempt_number_positive`: `CHECK (attempt_number > 0)`
6. **RecoveryCase Exactly-One Target Invariant:**
   * `ck_recovery_cases_ck_recovery_case_target_exactly_one`:
     ```sql
     CHECK (
       (payment_id IS NOT NULL AND subscription_id IS NULL)
       OR
       (payment_id IS NULL AND subscription_id IS NOT NULL)
     )
     ```
   Ensures every `RecoveryCase` references either a `Payment` OR a `Subscription`, but never both and never neither.

---

## 7. Indexes & Performance Rationale

* `ix_customers_external_customer_id` & `ix_customers_email`: Fast lookup during customer ingestion and webhook routing.
* `ix_payments_external_payment_id`: Fast lookup on gateway webhook callbacks.
* `ix_payments_customer_id` & `ix_subscriptions_customer_id`: Fast retrieval of customer payment and subscription history.
* `ix_payments_status` & `ix_subscriptions_status`: Efficient querying for failed transactions and at-risk subscriptions.
* `ix_payments_created_at` & `ix_payment_attempts_attempted_at`: Temporal range queries for risk detection windows.
* `ix_payment_attempts_payment_id`: Fast attempt history traversal for a given payment.
* `ix_recovery_cases_status` & `ix_recovery_cases_detected_at`: High-throughput queue polling for active recovery pipelines.
* `ix_recovery_cases_payment_id` & `ix_recovery_cases_subscription_id`: Direct joins between recovery cases and underlying payment/subscription records.

---

## 8. Why `Payment` and `PaymentAttempt` are Separate

In modern payment systems, a customer's logical intent to pay an amount (a `Payment` / Order) may involve multiple distinct tries (e.g., initial card decline due to 3DS timeout, followed by a successful retry or an alternate card attempt).

* **`Payment`**: Represents the commercial obligation, total amount, and ultimate status.
* **`PaymentAttempt`**: Captures transient execution data (gateway timestamps, attempt number, specific decline codes like `CARD_DECLINED` or `INSUFFICIENT_FUNDS`, error reasons).

Separating these entities enables accurate payment history analysis without mutating the original order record or losing audit visibility.

---

## 9. Why `RecoveryCase` is Only a Recovery-Opportunity Record

In Phase 1, `RecoveryCase` is strictly a data structure representing an identified revenue-at-risk opportunity.

It intentionally **does NOT** contain:
* AI diagnostic reasoning or prompt outputs (Phase 4).
* Recovery probability scores (Phase 4).
* Recommended interventions (Phase 5).
* Policy gateway approval decisions (Phase 6).
* Gateway execution responses or webhooks (Phase 7).

Keeping `RecoveryCase` lean in Phase 1 ensures clean architectural separation between data representations, AI reasoning, and deterministic execution.

---

## 10. Explicitly Deferred Future Functionality

* **Phase 2:** Synthetic data generator for populating test failures and customer patterns.
* **Phase 3:** Deterministic revenue-risk detection rules.
* **Phase 4:** AI root-cause diagnosis engine.
* **Phase 5:** Recovery decision agent.
* **Phase 6:** Policy and safety gateway.
* **Phase 7:** Razorpay Test Mode execution and webhook listeners.
* **Phase 8:** Audit trail logs and observability metrics.
