# Phase 3 — Deterministic Revenue-Risk Engine

## 1. Objective
Build a deterministic, rule-based revenue-risk evaluation engine (Baseline Version `v1`) that extracts observable transaction and customer signals, predicts recovery viability, assesses financial risk levels, and calculates reproducible benchmark evaluation metrics against synthetic ground truth without using LLMs or machine learning.

## 2. Scope & Core Requirements
1. **Separation of Concepts:**
   - `predicted_recoverable` (Boolean): Does baseline believe the case is recoverable?
   - `risk_level` (Enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`): Severity and financial exposure level.
2. **Observable Signal Extractor:**
   - Computes customer payment counts, historical success rate (in integer basis points: 0-10000 bps).
   - Extracts `target_attempt_count` (exact number of PaymentAttempts associated with the current Payment; 0 for Subscriptions).
   - Uses only actual Phase 1 fields (`Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase`).
3. **Deterministic Ruleset (`baseline_version = "v1"`):**
   - Distinct reason codes: `RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS`, `RC_CHRONIC_DECLINE_HISTORY`, `RC_TRANSIENT_FAILURE_PROVEN_HISTORY`, `RC_INSUFFICIENT_FUNDS`, `RC_SUBSCRIPTION_BILLING_GLITCH`, `RC_FIRST_TIME_CHECKOUT_DROP`, `RC_HIGH_VALUE_EXPOSURE`, `RC_UNRESOLVED_HARD_DECLINE`.
   - Explicit precedence: Negative failure invariants override positive signals; evidence accumulates across all matching rules.
   - High-value transactions (>= ₹5,000 / 500,000 paise) attach `RC_HIGH_VALUE_EXPOSURE` and elevate risk level without forcing recoverability.
4. **Air-Gapped Evaluation Layer & Target Matching:**
   - Evaluator matches predictions to `RecoveryGroundTruth` via `case_id` or `(target_type, target_id)`.
   - Shuffled evaluation order invariant.
5. **Integer Metrics & Zero-Division Safety:**
   - Confusion matrix (TP, FP, TN, FN).
   - Precision, Recall, F1, Accuracy in integer basis points (0-10000 bps) with safe zero-denominator fallbacks (0 bps).
   - Recoverable Amount Captured (TP amount in paise), Recoverable Amount Missed (FN amount in paise), False Intervention Amount (FP amount in paise).
   - Empty dataset returns 0 counts without raising exceptions.
6. **Reproducible Frozen Benchmark (`v1`):**
   - Published benchmark scorecard on standard 5,000-payment dataset.

## 3. Allowed Changes
* Creating modules in `services/risk_engine/`.
* Creating automated tests in `tests/test_risk_engine.py`.
* Creating documentation in `docs/risk-engine.md`.
* Updating `README.md` and `docs/PROJECT_CONTEXT.md`.

## 4. Forbidden Changes
* No AI/LLM integration, prompts, or neural networks.
* No Razorpay API calls or SDK dependencies.
* No payment execution or automatic retry logic.
* No modification of Phase 1 production database schema.
* No Phase 4 AI root-cause diagnosis logic.

## 5. Acceptance Criteria
1. All rules and reason codes adhere to explicit specification.
2. High-value rule flags financial exposure without overriding chronic failure negative invariants.
3. Air-gap test verifies `DeterministicRiskEngine` receives 0 ground truth fields.
4. Target matching evaluates correctly regardless of array ordering.
5. Zero-division and empty dataset edge cases handled gracefully (0 bps).
6. 100% of automated tests (Phase 0, Phase 1, Phase 2, Phase 3) pass.
7. Benchmark `v1` published and documented.

## 6. Completion Status
**COMPLETE** (Verified on 2026-08-31 with 53 passing tests, air-gapped evaluation harness, and frozen benchmark report docs/benchmark_v1.json).
