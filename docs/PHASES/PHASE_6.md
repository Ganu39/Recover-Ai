# Phase 6 — Deterministic Policy & Safety Gateway

## 1. Objective
Build a deterministic, fail-closed, auditable policy and safety gateway (`DeterministicSafetyGateway`, Gateway Version `v1`, Policy Version `v1`) that serves as the final non-execution boundary between Phase 5 recovery recommendations and a future Phase 7 execution layer.

## 2. Scope & Core Invariants
1. **Strict Non-Execution Boundary:**
   - Zero live payment execution, zero retries, zero Razorpay API imports, zero customer notifications, zero database write operations.
2. **The 12-Stage Safety Check Pipeline:**
   - 1. Fail-Safe Kill Switch Check
   - 2. Schema & Version Contract Validation (`decision_version="v1"`, `policy_version="v1"`, `gateway_version="v1"`)
   - 3. Independent Proposal Identity Verification (`uuid5`)
   - 4. Financial Integrity Verification (Strict integer minor units match between proposal and trusted context)
   - 5. Application Idempotency & Replay Protection
   - 6. Executable Action Allowlist (`RETRY_PAYMENT`, `RETRY_LATER`, `REQUEST_PAYMENT_METHOD_UPDATE`, `SUBSCRIPTION_RECOVERY_WORKFLOW`)
   - 7. Retry & Chronic Failure Defense-in-Depth (`target_attempt_count >= 3` strictly BLOCKED)
   - 8. Failure Category & Hard Decline Safety
   - 9. High-Value Safety & Explicit Human Approval Token Verification
   - 10. Sliding-Window Safety Rate Limiting
   - 11. Final Gate Authorization Synthesis
   - 12. Immutable Audit Record Emission
3. **Executable Action Allowlist:**
   - Permitted: `RETRY_PAYMENT`, `RETRY_LATER`, `REQUEST_PAYMENT_METHOD_UPDATE`, `SUBSCRIPTION_RECOVERY_WORKFLOW`.
   - Strictly Prohibited: `NO_ACTION` $\rightarrow$ `BLOCKED`; `HUMAN_REVIEW` $\rightarrow$ `REQUIRES_REVIEW`.
4. **Idempotency & Replay Protection:**
   - Exact duplicate proposal returns cached result with `is_replay = True` without consuming rate limit quotas.
   - Target conflict detection prevents contradictory interventions on identical targets.
5. **Fail-Closed Fail-Safe Kill Switch:**
   - System kill switch suspends all new authorizations (`KILL_SWITCH_ACTIVE`).
   - Missing or corrupted configuration fails closed.
6. **Air-Gap Preservation:**
   - Phase 6 consumes zero ground-truth evaluation labels and zero raw LLM tokens.

## 3. Allowed Changes
* Creating modules in `agents/gateway/`.
* Creating automated tests in `tests/test_safety_gateway.py`.
* Creating documentation in `docs/safety-gateway.md` and `docs/PHASES/PHASE_6.md`.
* Creating benchmark scorecard `docs/benchmark_gateway_v1.json`.
* Updating `docs/PROJECT_CONTEXT.md` and `docs/CHATGPT_CONTEXT.md`.

## 4. Forbidden Changes
* No Razorpay SDK imports, API calls, or webhooks.
* No live payment retry, charging, subscription cancellation, or refunds.
* No scheduler, background worker, or queue consumer.
* No writing to production database tables.
* No implementing Phase 7 execution adapters.

## 5. Acceptance Criteria
1. Gateway independently enforces retry cap ($\ge 3$), chronic decline blocks, and high-value approvals.
2. Proposal identity is independently recomputed and verified via UUID5.
3. Financial amounts are strictly preserved in integer paise without floating point.
4. Idempotency protects against replay and conflicting proposals for the same target.
5. Unsafe authorization rate across canonical benchmark dataset is exactly 0 bps (`unsafe_authorization_rate_bps == 0`).
6. 100% of automated tests pass across Phase 0 through Phase 6 (127 non-db tests).

## 6. Completion Status
**COMPLETE** (Verified on 2026-09-03 with 46 passing gateway tests, 127 total passing tests, 0 unsafe authorizations, and published gateway scorecard `docs/benchmark_gateway_v1.json`). Phase 7 remains **PLANNED**.
