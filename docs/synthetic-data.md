# RecoverAI — Synthetic Transaction Engine Documentation

This document describes the design, architecture, configuration, and validation of the **Synthetic Transaction Engine** built in **Phase 2** for RecoverAI.

---

## 1. Engine Architecture

The synthetic transaction engine generates realistic, correlated fintech datasets with deterministic pseudorandom number generation, temporal consistency, and strict separation between observable production entities and hidden evaluation ground truth.

```text
┌─────────────────────────────────────────────────────────────┐
│                 SyntheticDataGenerator                      │
│                  (Configured RNG Seed)                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
    ┌──────────────────────┐        ┌──────────────────────┐
    │  Observable Dataset  │        │ Evaluation Metadata  │
    │  (Production Layer)  │        │   (Hidden Layer)     │
    │──────────────────────│        │──────────────────────│
    │ • Customers (1:N)    │        │ • Case ID            │
    │ • Subscriptions      │        │ • Scenario Type      │
    │ • Payments           │        │ • is_recoverable     │
    │ • Payment Attempts   │        │ • Expected Reason    │
    │ • Recovery Cases     │        └──────────────────────┘
    └──────────┬───────────┘                   ▲
               │                               │
               ▼                               │ [Strict Air-Gap]
    ┌──────────────────────┐                   │ (Never exposed to
    │  PostgreSQL Database │                   │  AI decision inputs)
    │  (Phase 1 Entities)  │───────────────────┘
    └──────────────────────┘
```

---

## 2. Customer Behavioral Profiles

Customer profiles are parameterized using integer basis points (`bps`, where `10,000 bps = 100.00%`) and integer minor currency amounts (paise):

1. **`Reliable Customer` (`reliable`)**:
   - Success Rate: 9,000 bps (90%)
   - Ticket Range: ₹500 to ₹2,500 (`50,000` to `250,000` paise)
   - Payment Volume: 3 to 8 historical payments
2. **`Intermittent Customer` (`intermittent`)**:
   - Success Rate: 5,500 bps (55%)
   - Ticket Range: ₹300 to ₹3,500 (`30,000` to `350,000` paise)
   - Payment Volume: 2 to 6 historical payments
3. **`High-Value Customer` (`high_value`)**:
   - Success Rate: 8,500 bps (85%)
   - Ticket Range: ₹5,000 to ₹50,000 (`500,000` to `5,000,000` paise)
   - Payment Volume: 2 to 10 historical payments
4. **`Chronic Failure Customer` (`chronic_failure`)**:
   - Success Rate: 1,800 bps (18%)
   - Ticket Range: ₹200 to ₹1,500 (`20,000` to `150,000` paise)
   - Payment Volume: 2 to 7 historical payments
5. **`New Customer` (`new_customer`)**:
   - Success Rate: 7,000 bps (70%)
   - Ticket Range: ₹400 to ₹2,000 (`40,000` to `200,000` paise)
   - Payment Volume: 0 to 1 historical payments

---

## 3. Generic Failure Taxonomy

The generator utilizes generic gateway failure categories:
* `temporary_failure`: Transient network issue, gateway timeout, or momentary switch error.
* `insufficient_funds`: Balance deficit or card limit exceeded.
* `expired_payment_method`: Card expired or invalid mandate.
* `generic_decline`: Issuer refusal or policy restriction.
* `unknown_failure`: Uncategorized error.

---

## 4. Eight Scenario Archetypes & Configurable Weights

Scenario distributions are defined in configurable integer weights (basis points totaling 10,000 bps / 100%):

| Scenario ID | Default Weight (bps) | Ground Truth (`is_recoverable`) | Target Type |
|---|---|---|---|
| `high_probability_recoverable` | 2000 (20%) | `True` | Payment |
| `low_probability_recoverable` | 1500 (15%) | `True` | Payment |
| `clearly_non_recoverable` | 1500 (15%) | `False` | Payment |
| `new_customer` | 1000 (10%) | `True` | Payment |
| `repeated_failure` | 1000 (10%) | `False` | Payment |
| `temporary_failure_after_success_history` | 1500 (15%) | `True` | Payment |
| `subscription_failure` | 1000 (10%) | `True` | Subscription |
| `high_value_payment_failure` | 500 (5%) | `True` | Payment |

Detailed scenario rules are documented in [`docs/synthetic-scenarios.md`](synthetic-scenarios.md).

---

## 5. Ground-Truth Separation & Evaluation Layer

* **Hidden Ground Truth:** Each generated `RecoveryCase` has an associated `RecoveryGroundTruth` evaluation record containing `is_recoverable`, `scenario_type`, and `expected_recovery_reason`.
* **Air-Gap Guarantee:** Ground truth is strictly stored in the evaluation data layer. It is never stored in Phase 1 database tables and never included in observable serialized payloads sent to AI diagnostic components.

---

## 6. Deterministic Reproducibility

* **Deterministic RNG:** Uses Python's `random.Random(seed)`.
* **Deterministic UUIDs:** Generated using `uuid.UUID(bytes=rng.randbytes(16), version=4)`.
* **Deterministic Timestamps:** Generated relative to a fixed configuration reference date (`2026-01-01T00:00:00+00:00`).
* **Canonical Hashing:** `compute_dataset_hash(dataset)` outputs a SHA-256 hash uniquely identifying the dataset content. Identical seed and configuration produce bit-for-bit identical hashes.

---

## 7. Configuration & CLI Usage

### CLI Commands

Generate a dataset and print summary statistics:
```bash
python -m data.synthetic.cli --seed 42 --customers 1000 --payments 5000
```

Generate and seed directly into PostgreSQL:
```bash
python -m data.synthetic.cli --seed 42 --customers 1000 --payments 5000 --seed-db
```

### CLI Parameters
* `--seed`: Integer random seed (default: `42`).
* `--customers`: Exact number of customers (default: `1000`).
* `--payments`: Exact number of payments (default: `5000`).
* `--sub-bps`: Subscription ratio in basis points (default: `2500` / 25%).
* `--seed-db`: Flag to insert generated observable entities into PostgreSQL.

---

## 8. Data Quality Validation

The `DatasetValidator` performs automated invariant audits on generated datasets:
1. Validates unique external customer, payment, and subscription IDs.
2. Validates positive, sequential attempt numbering per payment.
3. Enforces the `RecoveryCase` exactly-one target constraint (`payment_id XOR subscription_id`).
4. Validates that all monetary amounts are non-negative integers.
5. Verifies chronological consistency across customer, payment, attempt, and recovery timelines.

---

## 9. Baseline 5,000-Payment Dataset Statistics (Seed 42)

* **Customers:** 1,000
* **Payments:** 5,000 (3,212 Successful, 1,788 Failed)
* **Payment Attempts:** 6,723
* **Subscriptions:** 232
* **Recovery Cases:** 1,676 (1,235 Recoverable, 441 Non-Recoverable)
* **Total Payment Amount:** 3,255,404,866 paise (~₹32.55M)
* **Failed Payment Amount:** 539,001,230 paise (~₹5.39M)
* **Amount at Risk:** 531,161,966 paise (~₹5.31M)
  - Recoverable Amount: 391,803,663 paise (~₹3.91M)
  - Non-Recoverable Amount: 139,358,303 paise (~₹1.39M)
* **Generation Duration:** 0.263 seconds
* **Validation Duration:** 0.033 seconds
* **Dataset SHA-256 Hash:** `2423ca5970c24a6a46688bf132256daf4beaf0997c90e9c2b9aacacd6def2fde`
