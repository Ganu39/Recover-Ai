# Phase 7 — Bounded Recovery Execution Layer

## 1. Objective
Build a tightly bounded, deterministic, and auditable recovery execution layer (`ExecutionService`, Version `v1`) that executes only Phase 6-approved recovery actions through an isolated provider adapter (supporting Razorpay Test Mode and deterministic mock simulation), while guaranteeing strict execution idempotency, bounded retries, state machine integrity, webhook replay safety, state reconciliation, and zero unauthorized executions.

---

## 2. Core Scope & Architectural Invariants

1. **Mandatory Phase 6 Authorization Gate:**
   * Phase 7 **never** executes actions directly from Phase 4 AI diagnoses, Phase 5 proposals, or external API parameters.
   * Execution requires an authentic [`GatewayDecisionResult`](file:///c:/Users/ganub/OneDrive/Desktop/buildathon1/agents/gateway/schemas.py) with `gateway_decision == GatewayDecision.APPROVED` and `eligible_for_execution_layer == True`.
   * Authorization is independently re-validated immediately before provider dispatch.

2. **Isolated Provider Adapter Boundary:**
   * Razorpay SDK interactions are strictly confined to [`services/execution/razorpay_provider.py`](file:///c:/Users/ganub/OneDrive/Desktop/buildathon1/services/execution/razorpay_provider.py) behind the [`BasePaymentProvider`](file:///c:/Users/ganub/OneDrive/Desktop/buildathon1/services/execution/provider.py) interface.
   * Phase 4, Phase 5, and Phase 6 remain 100% free of Razorpay imports.

3. **Strict Test-Mode Enforcement & Live-Mode Rejection:**
   * System runs exclusively with `RECOVERAI_PAYMENT_MODE=test` (or `simulation`).
   * Live mode (`live`) or live credentials (`rzp_live_...`) are strictly prohibited and immediately fail closed.
   * Configuration missing, corrupt, or pointing to live mode terminates with fail-closed refusal.

4. **Action Execution Semantics:**
   * `RETRY_PAYMENT`: Dispatches a payment recovery attempt through the configured provider adapter.
   * `RETRY_LATER`: Transitions to `DEFERRED` status; does **not** execute immediately (no premature retry).
   * `REQUEST_PAYMENT_METHOD_UPDATE`: Generates a controlled customer update request workflow state.
   * `SUBSCRIPTION_RECOVERY_WORKFLOW`: Initiates recurring billing recovery attempt if supported, else transitions safely.
   * `NO_ACTION` and `HUMAN_REVIEW`: Strictly rejected from execution.

5. **Deterministic Execution Idempotency:**
   * Execution idempotency key is derived deterministically:
     $$\text{idempotency\_key} = \text{uuid5}(\text{NAMESPACE\_DNS}, \text{"recoverai-exec-\{proposal\_id\}-\{gateway\_version\}-\{policy\_version\}-\{action\_type\}"})$$
   * Re-submitting the same proposal returns the existing execution state; zero duplicate provider charges.

6. **Bounded Retries:**
   * Hard attempt ceiling independently enforced: maximum attempts authorized by Phase 6 policy (max 2 attempts; attempt $\ge 3$ strictly blocked).
   * Transport/network retries are strictly decoupled from payment attempt counters.

7. **Explicit Execution State Machine:**
   * Valid transitions:
     $$\text{AUTHORIZED} \rightarrow \text{EXECUTION\_STARTED} \rightarrow \text{PROVIDER\_REQUESTED}$$
     $$\text{PROVIDER\_REQUESTED} \rightarrow \{\text{SUCCEEDED}, \text{FAILED}, \text{UNKNOWN\_PROVIDER\_STATE}, \text{REQUIRES\_REVIEW}\}$$
     $$\text{SUCCEEDED} \rightarrow \text{RECONCILED}$$
     $$\text{UNKNOWN\_PROVIDER\_STATE} \rightarrow \{\text{RECONCILED}, \text{FAILED}, \text{REQUIRES\_REVIEW}\}$$
     $$\text{AUTHORIZED} \rightarrow \text{DEFERRED} \quad (\text{for } \text{RETRY\_LATER})$$
   * Any invalid transition fails closed safely.

8. **Webhook Security & Replay Protection:**
   * HMAC-SHA256 signature verification on all incoming webhook payloads.
   * Processed provider event references are tracked; duplicate webhooks are processed idempotently as no-ops.
   * Webhooks reconcile state; they **never** trigger fresh payment attempts.

9. **Financial Integrity & Integer Minor Units:**
   * All execution amounts are strictly integer paise (`amount_minor: int`, `currency: str`).
   * Zero floating-point arithmetic.
   * Execution amount must exactly match the Phase 6 authorized amount.

10. **Separation of Authorized vs Recovered Revenue:**
    * Clearly differentiates:
      * `amount_at_risk`
      * `authorized_amount`
      * `attempted_amount`
      * `provider_confirmed_amount`
      * `recovered_amount`
    * Only provider-confirmed successful transactions are counted as recovered revenue.

---

## 3. Allowed Changes
* Creating modules in `services/execution/`.
* Creating database entity model in `data/models/recovery_execution.py`.
* Updating `data/models/__init__.py`.
* Creating automated test suite in `tests/test_execution_layer.py`.
* Creating documentation in `docs/execution-layer.md` and `docs/PHASES/PHASE_7.md`.
* Updating `docs/PROJECT_CONTEXT.md` and `docs/CHATGPT_CONTEXT.md`.

## 4. Forbidden Changes
* No live Razorpay API calls or live credentials.
* No bypassing Phase 6 gateway authorization.
* No execution calls from Phase 4 AI or Phase 5 proposals.
* No floating-point financial arithmetic.
* No arbitrary external URL calls or unvalidated webhook handling.
* No unconstrained retries beyond Phase 6 policy.

---

## 5. Acceptance Criteria
1. Only Phase 6-approved proposals with `eligible_for_execution_layer = True` can execute.
2. Authorization is re-validated immediately before provider execution.
3. Provider abstraction supports both `MockPaymentProvider` (unit/benchmark) and `RazorpayTestProvider` (test mode).
4. Live credentials or live mode strictly fail closed.
5. Deterministic idempotency key prevents duplicate execution across retries and restarts.
6. Execution state machine enforces valid transitions and handles timeouts as `UNKNOWN_PROVIDER_STATE`.
7. Webhook handling validates signatures, rejects replay, and reconciles state without triggering payments.
8. Critical safety metric: `UNAUTHORIZED_EXECUTION_RATE == 0`.
9. Critical safety metric: `DUPLICATE_EXECUTION_RATE == 0`.
10. Full regression suite across Phases 0–7 passes 100%.

---

## 6. Implementation Status
**COMPLETE**

* **Automated Tests:** 50/50 tests PASSED in 0.62s (`tests/test_execution_layer.py`).
* **Full Regression Suite:** 177 tests PASSED in 1.30s across Phases 0–7.
* **Release Safety Metrics:**
  - `UNAUTHORIZED_EXECUTION_RATE`: **0 bps** (0 violations)
  - `DUPLICATE_EXECUTION_RATE`: **0 bps** (0 violations)
  - `FINANCIAL_INTEGRITY_VIOLATION_RATE`: **0 bps** (0 violations)
* **Canonical Benchmark (`seed=42`, 1,676 Proposals):**
  - Total Evaluated: 1,676 proposals
  - Phase 6 Authorized: 689 (85,259,735 paise)
  - Executions Attempted: 456 (56,195,598 paise)
  - Executions Deferred (Cooldown): 233 (29,064,137 paise)
  - Confirmed Recovered Revenue: **56,195,598 paise (~₹561.9k)**
  - Unsafe / Duplicate / Financial Violations: **0**
