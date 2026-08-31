# RecoverAI — Deterministic Revenue-Risk Engine (Baseline v1)

This document provides the canonical specification, rule definitions, evidence codes, mathematical formulations, and frozen benchmark results for the **Deterministic Revenue-Risk Engine** built in **Phase 3**.

---

## 1. Engine Purpose & Architecture

The Deterministic Revenue-Risk Engine operates as the non-AI baseline for RecoverAI. It analyzes observable customer payment histories, transaction attempt counts, gateway decline codes, and subscription statuses to predict recovery viability and classify financial exposure.

```text
Observable Data Layer (PostgreSQL / Synthetic ObservableDataset)
        │
        ▼
[ Observable Feature Extractor (services/risk_engine/extractor.py) ]
   ├── Customer historical payment count & success rate (in integer bps)
   ├── Current transaction attempt count & latest gateway decline code
   └── Subscription status & financial amount at risk
        │
        ▼
[ Deterministic Rule Engine (services/risk_engine/engine.py - v1) ]
   ├── Evaluates ObservableRiskContext against frozen ruleset
   └── Emits RiskEvaluationResult (predicted_recoverable, risk_level, evidence)
        │
        ├─────────────────────────────────────────────┐
        ▼ (Downstream Evaluation Harness Only)         ▼ (Strictly Air-Gapped)
[ Baseline Evaluator (services/risk_engine/evaluator.py) ] ◄── [ RecoveryGroundTruth ]
   ├── Target Matching by case_id / (target_type, target_id)
   ├── Confusion Matrix & Basis-Point Metrics (0-10000 bps)
   └── Integer Minor Financial Reconciliations (paise)
```

---

## 2. Separation of Recoverability and Financial Exposure

* **`predicted_recoverable` (`bool`):**
  Answers whether the deterministic baseline believes an intervention will succeed based on historical intent and transaction failure category.
* **`risk_level` (`RiskLevel`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`):**
  Answers the operational urgency and magnitude of financial exposure.
  * `LOW`: Minimal recovery friction (e.g. high-reliability customer with transient switch error).
  * `MEDIUM`: Standard actionable recovery opportunity (e.g. new customer checkout drop, insufficient funds).
  * `HIGH`: Elevated financial exposure ($\ge ₹5,000$) or unclassified decline without mitigating history.
  * `CRITICAL`: Severe financial exposure ($\ge ₹5,000$ with chronic failure) or unrecoverable exhausted attempts.

> **Key Rule:** High transaction amount ($\ge ₹5,000$) attaches `RC_HIGH_VALUE_EXPOSURE` and elevates `risk_level`, but does **NOT** force `predicted_recoverable = True`.

---

## 3. Observable Input Contract (`ObservableRiskContext`)

The engine consumes only observable production fields:
* `target_type`: `"payment"` or `"subscription"`.
* `target_id`: Unique target UUID.
* `customer_id`: Unique customer UUID.
* `amount_at_risk_minor`: Integer minor units (paise).
* `currency`: Currency code (`"INR"`).
* `customer_history_count`: Number of prior completed payments for customer.
* `customer_success_count`: Number of prior captured payments for customer.
* `customer_success_rate_bps`: Historical success rate in basis points (`0` to `10000` bps).
* `target_attempt_count`: Exact number of `PaymentAttempt` records for current payment (`0` for subscriptions).
* `latest_failure_code`: Most recent gateway decline code (`temporary_failure`, `insufficient_funds`, `expired_payment_method`, `generic_decline`, `unknown_failure`).
* `subscription_status`: Current status string (`active`, `past_due`, `cancelled`, `halted`).

---

## 4. Observable Evidence Reason Codes

| Reason Code | Description | Observed Metric |
|---|---|---|
| `RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS` | Payment has $\ge 3$ consecutive failed attempts | `attempts >= 3` |
| `RC_CHRONIC_DECLINE_HISTORY` | Customer success rate $< 25\%$ across $\ge 3$ past payments with hard decline | `success_rate < 2500 bps` |
| `RC_TRANSIENT_FAILURE_PROVEN_HISTORY` | Proven customer ($\ge 75\%$ success rate) with transient decline code | `success_rate >= 7500 bps` |
| `RC_INSUFFICIENT_FUNDS` | Payment declined due to balance deficit on actionable attempt | `failure_code == insufficient_funds` |
| `RC_SUBSCRIPTION_BILLING_GLITCH` | Active subscription transitioned to `past_due` billing state | `subscription_status == past_due` |
| `RC_FIRST_TIME_CHECKOUT_DROP` | New customer checkout drop-off with $\le 1$ prior transaction | `history_count <= 1` |
| `RC_HIGH_VALUE_EXPOSURE` | Transaction value $\ge ₹5,000$ (500,000 paise) | `amount >= 500000 paise` |
| `RC_UNRESOLVED_HARD_DECLINE` | Unclassified decline or insufficient recovery signals | `failure == generic_decline` |

---

## 5. Frozen Baseline Ruleset (`baseline_version = "v1"`)

### Rule Precedence & Decision Policy
1. **High-Value Exposure:** If `amount_at_risk_minor >= 500000`, attach `RC_HIGH_VALUE_EXPOSURE`.
2. **Negative Invariants (Precedence 1):**
   * If `target_attempt_count >= 3` $\rightarrow$ `predicted_recoverable = False`, `RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS`.
   * Else if `customer_history_count >= 3` AND `customer_success_rate_bps < 2500` AND `latest_failure_code in ('generic_decline', 'unknown_failure')` $\rightarrow$ `predicted_recoverable = False`, `RC_CHRONIC_DECLINE_HISTORY`.
3. **Positive Signals (Precedence 2):**
   * Else if `target_type == 'subscription'` AND `subscription_status == 'past_due'` $\rightarrow$ `predicted_recoverable = True`, `RC_SUBSCRIPTION_BILLING_GLITCH`.
   * Else if `customer_history_count >= 2` AND `customer_success_rate_bps >= 7500` AND `latest_failure_code in ('temporary_failure', 'generic_decline')` $\rightarrow$ `predicted_recoverable = True`, `RC_TRANSIENT_FAILURE_PROVEN_HISTORY`.
   * Else if `latest_failure_code == 'insufficient_funds'` AND `target_attempt_count <= 2` $\rightarrow$ `predicted_recoverable = True`, `RC_INSUFFICIENT_FUNDS`.
   * Else if `customer_history_count <= 1` AND `target_attempt_count <= 2` $\rightarrow$ `predicted_recoverable = True`, `RC_FIRST_TIME_CHECKOUT_DROP`.
4. **Fallback:**
   * Else $\rightarrow$ `predicted_recoverable = False`, `RC_UNRESOLVED_HARD_DECLINE`.

---

## 6. Evaluation Methodology & Metrics

### Mathematical Formulations
* $\text{Precision (bps)} = \lfloor \frac{TP \times 10000}{TP + FP} \rfloor$ (or `0` bps if $TP + FP = 0$)
* $\text{Recall (bps)} = \lfloor \frac{TP \times 10000}{TP + FN} \rfloor$ (or `0` bps if $TP + FN = 0$)
* $\text{F1 Score (bps)} = \lfloor \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} \rfloor$ (or `0` bps if $\text{Precision} + \text{Recall} = 0$)
* $\text{Recoverable Amount Captured} = \sum_{i \in TP} \text{Amount}_i$ (Paise)
* $\text{Recoverable Amount Missed} = \sum_{i \in FN} \text{Amount}_i$ (Paise)
* $\text{False Intervention Amount} = \sum_{i \in FP} \text{Amount}_i$ (Paise)
* $\text{Revenue Capture Rate (bps)} = \lfloor \frac{\text{Captured Amount} \times 10000}{\text{Total Recoverable Ground Truth Amount}} \rfloor$

---

## 7. Frozen Baseline Benchmark Results (`v1`)

Benchmark generated against standard synthetic dataset (`Seed 42`, 1,000 Customers, 5,000 Payments):

* **Evaluated Cases:** 1,676
* **Confusion Matrix:**
  * **True Positives (TP):** 522
  * **False Positives (FP):** 181
  * **True Negatives (TN):** 260
  * **False Negatives (FN):** 713
* **Statistical Performance:**
  * **Precision:** 7,425 bps (74.25%)
  * **Recall:** 4,226 bps (42.26%)
  * **F1 Score:** 5,386 bps (53.86%)
  * **Accuracy:** 4,665 bps (46.65%)
* **Financial Metrics (Paise):**
  * **Total Amount at Risk:** 531,161,966 paise (~₹5.31M)
  * **Recoverable Amount Captured (TP):** 196,495,127 paise (~₹1.96M)
  * **Recoverable Amount Missed (FN):** 195,308,536 paise (~₹1.95M)
  * **False Intervention Amount (FP):** 61,971,831 paise (~₹0.62M)
  * **Revenue Capture Rate:** 5,015 bps (50.15%)
* **Rule Firing Counts:**
  * `RC_FIRST_TIME_CHECKOUT_DROP`: 412
  * `RC_TRANSIENT_FAILURE_PROVEN_HISTORY`: 250
  * `RC_UNRESOLVED_HARD_DECLINE`: 645
  * `RC_CHRONIC_DECLINE_HISTORY`: 218
  * `RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS`: 110
  * `RC_HIGH_VALUE_EXPOSURE`: 108
  * `RC_SUBSCRIPTION_BILLING_GLITCH`: 44
  * `RC_INSUFFICIENT_FUNDS`: 41

---

## 8. CLI Usage

To evaluate the baseline against any synthetic seed and export benchmark results:
```bash
python -m services.risk_engine.cli --seed 42 --customers 1000 --payments 5000 --output docs/benchmark_v1.json
```
