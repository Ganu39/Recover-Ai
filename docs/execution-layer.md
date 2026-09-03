# Phase 7 — Bounded Recovery Execution Layer

## 1. Architecture Overview

Phase 7 implements the **Bounded Recovery Execution Layer** (`ExecutionService`, Version `v1`), the final operational boundary of RecoverAI. It executes Phase 6-approved recovery actions through an isolated provider adapter (Razorpay Test Mode or deterministic Mock simulation) while guaranteeing zero unauthorized executions, persistent idempotency, bounded retries, explicit state machine transitions, webhook replay safety, state reconciliation, and complete auditability.

```text
Phase 5: Recovery Decision Proposal (Recommendation)
                  │
                  ▼
Phase 6: Deterministic Safety Gateway (Policy Gatekeeper)
                  │ (APPROVED + eligible_for_execution_layer=True)
                  ▼
┌──────────────────────────────────────────────────────────────┐
│   PHASE 7: Bounded Recovery Execution Layer                  │
│                                                              │
│  Stage 1: Pre-Execution Authorization Re-validation          │
│  Stage 2: Deterministic Execution Idempotency (UUID5)        │
│  Stage 3: Atomic In-Flight Concurrency Lock                  │
│  Stage 4: Action Execution Semantics Dispatch                │
│           ├── RETRY_LATER -> DEFERRED (Cooldown Hold)        │
│           └── Executable Actions -> Provider Dispatch        │
│  Stage 5: Isolated Provider Adapter (Test Mode / Mock)       │
│  Stage 6: Normalized Provider Response Classification        │
│  Stage 7: Execution State Machine Enforcement                │
│  Stage 8: Webhook Replay Protection & Signature Validation   │
│  Stage 9: State Reconciliation Protocol                      │
│  Stage 10: Append-Only Execution Audit Logging               │
└──────────────────────────────┬───────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
   MockPaymentProvider                   RazorpayTestProvider
(Deterministic Simulation)             (Strict Test Mode rzp_test_)
            │                                     │
            ▼                                     ▼
   State Reconciliation                  State Reconciliation
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                   Actual Recovered Revenue
                (Provider-Confirmed Outcomes)
```

---

## 2. Core Operational & Safety Rules

1. **Mandatory Phase 6 Precedence:**
   * Phase 7 executes **only** actions authorized by Phase 6 with `gateway_decision == APPROVED` and `eligible_for_execution_layer == True`.
   * Authorization is independently re-validated immediately before provider dispatch.
   * AI cannot authorize execution, modify parameters, or bypass Phase 6.

2. **Strict Test Mode & Live Key Rejection:**
   * Execution requires `RECOVERAI_PAYMENT_MODE=test` (or `simulation`).
   * Any `rzp_live_...` key, live environment mode, or missing mode immediately raises `SecurityError` and fails closed.

3. **Deterministic Execution Idempotency:**
   * Logical execution identity is derived deterministically:
     $$\text{idempotency\_key} = \text{uuid5}(\text{NAMESPACE\_DNS}, \text{"recoverai-exec-\{proposal\_id\}-\{gateway\_version\}-\{policy\_version\}-\{action\_type\}"})$$
   * Re-submitting the same proposal returns the existing execution state without re-calling the payment provider.

4. **Bounded Action Semantics:**
   * `RETRY_PAYMENT`: Dispatches recovery payment attempt through provider adapter.
   * `RETRY_LATER`: Transitions to `DEFERRED` status; does **not** execute immediately.
   * `REQUEST_PAYMENT_METHOD_UPDATE`: Initiates payment method update workflow.
   * `SUBSCRIPTION_RECOVERY_WORKFLOW`: Initiates subscription billing recovery attempt.
   * `NO_ACTION` and `HUMAN_REVIEW`: Strictly rejected from execution.

5. **Execution State Machine:**
   * Legal transitions:
     $$\text{AUTHORIZED} \rightarrow \text{EXECUTION\_STARTED} \rightarrow \text{PROVIDER\_REQUESTED}$$
     $$\text{PROVIDER\_REQUESTED} \rightarrow \{\text{SUCCEEDED}, \text{FAILED}, \text{UNKNOWN\_PROVIDER\_STATE}, \text{REQUIRES\_REVIEW}\}$$
     $$\text{SUCCEEDED} \rightarrow \text{RECONCILED}$$
     $$\text{UNKNOWN\_PROVIDER\_STATE} \rightarrow \{\text{RECONCILED}, \text{FAILED}, \text{REQUIRES\_REVIEW}\}$$
     $$\text{AUTHORIZED} \rightarrow \text{DEFERRED} \quad (\text{for } \text{RETRY\_LATER})$$

6. **Ambiguous Provider State & Timeouts:**
   * Transport timeouts, connection resets, or network errors transition to `UNKNOWN_PROVIDER_STATE`.
   * Timeouts are **never** treated as automatic failure and **never** trigger blind duplicate payment requests.
   * Reconciliation is performed via status queries or provider webhooks.

7. **Cryptographic Webhook Verification:**
   * Webhook payloads are verified using HMAC-SHA256 signatures against the webhook secret.
   * Replay protection tracks processed provider event references (`event_id`); duplicate deliveries are safe no-ops.
   * Webhooks reconcile existing execution records; they **never** trigger fresh payment attempts.

8. **Financial Integrity & Integer Minor Units:**
   * All monetary quantities are strictly integer paise (`amount_minor: int`, `currency: str`).
   * Zero floating-point arithmetic.
   * Execution amount must exactly match the Phase 6 authorized amount.

---

## 3. Revenue Recovery Metrics vs Authorizations

| Metric | Definition | Seed 42 Benchmark |
| :--- | :--- | :--- |
| **Total Amount at Risk** | Gross failed transaction amount evaluated | ₹5,311,619.66 (531,161,966 paise) |
| **Phase 6 Authorized Amount** | Amount approved by Phase 6 gateway | ₹852,597.35 (85,259,735 paise) |
| **Executions Attempted Amount** | Amount dispatched to payment provider | ₹561,955.98 (56,195,598 paise) |
| **Executions Deferred Amount** | Amount held in cooldown (`RETRY_LATER`) | ₹290,641.37 (29,064,137 paise) |
| **Provider Confirmed Amount** | Amount confirmed successful by provider | ₹561,955.98 (56,195,598 paise) |
| **Confirmed Recovered Revenue** | Authoritative reconciled recovered revenue | **₹561,955.98 (56,195,598 paise)** |
| **Unauthorized Execution Rate** | Unauthorized executions divided by attempts | **0 bps (Target: 0 bps)** |
| **Duplicate Execution Rate** | Duplicate executions caused by RecoverAI | **0 bps (Target: 0 bps)** |
| **Financial Integrity Violation Rate** | Mismatched amount/currency instances | **0 bps (Target: 0 bps)** |

---

## 4. Known Limitations & Boundaries
* **Test Mode Only:** Live payments are strictly prohibited by code, configuration, and security tests.
* **Persistent Database Model:** `RecoveryExecution` table schema is migration-ready (`0002_recovery_executions.py`). In-memory storage is used for unit benchmarks; PostgreSQL database integration connects when running with live asyncpg database instance.
