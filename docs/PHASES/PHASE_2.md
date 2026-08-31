# Phase 2 — Synthetic Transaction Engine

## 1. Objective
Build a deterministic, reproducible synthetic transaction engine that creates realistic customer behavior profiles, payment histories, gateway attempts, subscription failures, and recovery opportunity scenarios with integer-based probabilities, independent behavioral dimensions, and strictly separated hidden ground-truth evaluation metadata.

## 2. Scope & Core Requirements
1. **Integer Probability & Arithmetic:**
   - 0-9999 basis points for all probability decisions (e.g., 85% = 8500).
   - Zero floating-point logic for money, probabilities, weights, or statistics.
2. **Behavioral Profiles:**
   - Reliable Customer, Intermittent Customer, High-Value Customer, Chronic Failure Customer, New Customer.
   - Fully decoupled from scenario outcome rules.
3. **8 Scenario Archetypes & Integer Distribution:**
   - `high_probability_recoverable` (weight: 2000 / 20%)
   - `low_probability_recoverable` (weight: 1500 / 15%)
   - `clearly_non_recoverable` (weight: 1500 / 15%)
   - `new_customer` (weight: 1000 / 10%)
   - `repeated_failure` (weight: 1000 / 10%)
   - `temporary_failure_after_success_history` (weight: 1500 / 15%)
   - `subscription_failure` (weight: 1000 / 10%)
   - `high_value_payment_failure` (weight: 500 / 5%)
4. **Strict Ground-Truth Separation:**
   - `ObservableDataset`: Production-compatible entities only.
   - `EvaluationMetadata`: Hidden ground-truth (`case_id`, `scenario_type`, `is_recoverable`, `expected_recovery_reason`).
   - Ground-truth never stored in Phase 1 database tables or observable serialization.
5. **Exact Record Counts & Reproducibility:**
   - `customers = N` -> exactly N Customers.
   - `payments = M` -> exactly M Payments.
   - Deterministic UUIDs and deterministic timestamps relative to a fixed `reference_date`.
   - Identical seed + config produces bit-for-bit identical SHA-256 dataset hash.
6. **Documentation & Validation:**
   - Canonical scenario reference in `docs/synthetic-scenarios.md`.
   - Comprehensive documentation in `docs/synthetic-data.md`.
   - Validation utility with zero-tolerance rule checks.
   - Integer minor financial statistics reconciliation.
   - Safe PostgreSQL seeding transaction.

## 3. Allowed Changes
* Creating synthetic generator modules under `data/synthetic/`.
* Creating `docs/synthetic-scenarios.md` and `docs/synthetic-data.md`.
* Creating automated tests under `tests/test_synthetic.py`.
* Updating `README.md` and `docs/PROJECT_CONTEXT.md`.

## 4. Forbidden Changes
* No AI/LLM integration or prompts.
* No Razorpay API calls or SDK dependencies.
* No payment execution or automatic retry logic.
* No modification of Phase 1 production database schema.
* No Phase 3 deterministic recovery engine implementation.

## 5. Acceptance Criteria
1. Same seed produces 100% identical dataset and SHA-256 hash; different seed produces different dataset.
2. Generates all 5 customer profiles, realistic attempts, subscriptions, and all 8 recovery scenarios.
3. Hidden ground-truth metadata generated strictly outside the production schema and absent from observable payloads.
4. Exactly N customers and M payments generated.
5. Data quality validator passes with 0 constraint violations.
6. Seeding utility successfully seeds into isolated PostgreSQL database without schema modifications.
7. Dataset statistics reconcile with generated records using integer minor units.
8. Large-scale dataset test (1,000 customers, 5,000 payments) runs efficiently and validates.
9. Automated tests (Phase 0, Phase 1, Phase 2) all pass.

## 6. Completion Status
**COMPLETE** (Verified on 2026-08-31 with 37 passing tests and verified large-scale dataset generation).
