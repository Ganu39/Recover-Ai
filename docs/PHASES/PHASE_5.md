# Phase 5 — Recovery Decision Agent

## 1. Objective
Build a deterministic, policy-governed recovery recommendation engine (`RecoveryDecisionAgent`, Version `v1`, Policy `v1`) that combines observable transaction contexts, Phase 4 AI root-cause diagnoses, and deterministic safety rules to synthesize structured decision proposals without performing any financial execution.

## 2. Scope & Core Invariants
1. **Strict Non-Execution Decision Boundary:**
   - Zero payment execution, zero retries, zero Razorpay API dependencies, zero customer notifications, zero database write operations.
2. **Explicit Precedence Hierarchy:**
   - 1. Deterministic Safety Hard Blocks (Attempt count $\ge 3$, Chronic decline history) $\rightarrow$ `NO_ACTION` / `BLOCKED` (Always takes precedence, even over high-value escalation).
   - 2. High-Value Escalation (Amount $\ge ₹5,000$) $\rightarrow$ `HUMAN_REVIEW` / `REQUIRES_REVIEW` (`requires_human_approval = True`).
   - 3. Deterministic Domain Routing (Subscription workflow, Expired card update, Insufficient funds cooldown).
   - 4. AI Diagnostic Context (Evidence interpretation, qualitative rationale).
3. **Deterministic Identity:**
   - `proposal_id` is deterministically derived using `uuid.uuid5` from `(decision_version, policy_version, target_type, target_id)`.
4. **Trusted Input & Money Safety:**
   - Financial amounts (`amount_minor`, `currency`) are copied strictly from trusted observable contexts. AI never computes or provides financial amounts.
5. **Action Taxonomy (`RecoveryActionType`):**
   - `NO_ACTION`, `RETRY_PAYMENT`, `RETRY_LATER`, `REQUEST_PAYMENT_METHOD_UPDATE`, `SUBSCRIPTION_RECOVERY_WORKFLOW`, `HUMAN_REVIEW`.
6. **Proposal Status (`DecisionStatus`):**
   - `PROPOSED`, `REQUIRES_REVIEW`, `BLOCKED`, `NO_ACTION`.
7. **Traceable Explanation Chain:**
   - `observed_facts`, `ai_inferences`, `policy_checks`, `final_rationale`.
8. **Ground-Truth Air-Gap:**
   - `DecisionInputContext` contains zero evaluation metadata. Tested via input serialization audit.

## 3. Allowed Changes
* Creating modules in `agents/decision/`.
* Creating automated tests in `tests/test_recovery_decision.py`.
* Creating documentation in `docs/recovery-decision.md`.
* Updating `README.md`, `docs/PROJECT_CONTEXT.md`, and `docs/CHATGPT_CONTEXT.md`.

## 4. Forbidden Changes
* No live payment execution, retries, or Razorpay API calls.
* No scheduler or background worker implementation.
* No modifying database entities or production tables.
* No Phase 6 policy gateway implementation.

## 5. Acceptance Criteria
1. Hard safety blocks strictly override high-value escalation and AI recommendations.
2. Proposal IDs are 100% deterministic across runs with identical inputs and policy versions.
3. Financial amounts are strictly preserved as integer minor units from observable contexts.
4. AI diagnosis failures gracefully fall back to policy-governed review or safe blocking.
5. Ground-truth air-gap is preserved and verified by automated tests.
6. 100% of automated tests pass across Phase 0, 1, 2, 3, 4, and 5 (95+ tests).

## 6. Completion Status
**COMPLETE** (Verified on 2026-08-31 with 100 passing tests, deterministic proposal IDs, strict policy supremacy, and published decision scorecard docs/benchmark_decision_v1.json).
