# RecoverAI — Recovery Decision Agent (Phase 5)

This document provides the canonical specification, decision taxonomy, policy precedence hierarchy, safety invariants, explanation chain, and benchmark results for the **Recovery Decision Agent** (`decision_version = "v1"`, `policy_version = "v1"`).

---

## 1. Objective & Non-Execution Boundary

The Recovery Decision Agent operates as the policy-first recommendation layer of RecoverAI. It synthesizes structured recovery decision proposals by combining observable transaction context, Phase 4 AI root-cause diagnoses, and deterministic safety rules.

### Strict Execution Boundaries
* **Proposal Only:** The agent produces structured decision proposals (`RecoveryDecisionProposal`). It has **zero Razorpay API access**, **zero payment execution tools**, **zero notification tools**, and **zero database write capabilities**.
* **Deterministic Policy Supremacy:** AI diagnosis provides qualitative context and evidence interpretation, but deterministic safety policies have absolute authority. The AI can never override retry limits, high-value escalation thresholds, or hard decline blocks.
* **Integer Minor Units:** All monetary values are strictly copied from trusted observable contexts in integer minor units (paise). The AI never calculates or alters financial amounts.

```text
Observable Data Layer (Phase 1 Database / ObservableDataset)
        │
        ├─────────────────────────────────────────────┐
        ▼                                             ▼
[ Context Builder (Phase 4) ]             [ Deterministic Policy Layer ]
        │                                 (agents/decision/policy.py)
        ▼                                    ├── Max attempt threshold (<= 2)
[ AI Diagnosis Agent (Phase 4) ]             ├── High-value escalation (>= ₹5,000)
        │                                    ├── Blocked failure codes
        ▼                                    └── Subscriptions / Unclassified rules
[ AIDiagnosisResult (Untrusted AI Input) ]            │
        │                                             │
        └──────────────────────┬──────────────────────┘
                               │
                               ▼
[ Recovery Decision Agent (agents/decision/service.py) ]
   ├── Evaluates Hard Invariants & Policy Thresholds
   ├── Resolves Conflicting Signals (Policy > Invariants > AI Opinion)
   └── Synthesizes Structured RecoveryDecisionProposal
        │
        ├─────────────────────────────────────────────┐
        ▼ (Downstream Evaluation Only)                ▼ (Strictly Air-Gapped)
[ Decision Evaluator (agents/decision/evaluator.py) ] ◄── [ RecoveryGroundTruth ]
   ├── Policy Compliance Rate & Safety Invariant Audits
   ├── Action Appropriateness vs Ground Truth
   └── Comparison against Baseline v1 & AI Diagnosis v1
```

---

## 2. Recovery Action Taxonomy (`RecoveryActionType`)

1. **`NO_ACTION`**: Unrecoverable opportunity (chronic declines, exhausted attempts, unmitigated fraud declines).
2. **`RETRY_PAYMENT`**: Automated gateway retry (transient network/switch glitch on proven reliable account with attempt count $< 3$).
3. **`RETRY_LATER`**: Scheduled retry candidate after cooldown window (insufficient funds / balance deficit).
4. **`REQUEST_PAYMENT_METHOD_UPDATE`**: Self-serve customer update link (expired card, invalid token, or new customer drop-off).
5. **`SUBSCRIPTION_RECOVERY_WORKFLOW`**: Recurring subscription recovery workflow for `past_due` billing states.
6. **`HUMAN_REVIEW`**: Operations escalation (orders $\ge ₹5,000$, conflicting signals, unknown decline codes, AI provider errors).

---

## 3. Decision Status Lifecycle (`DecisionStatus`)

* **`PROPOSED`**: Action approved by policy for automated processing in downstream execution layers.
* **`REQUIRES_REVIEW`**: Action blocked from automated execution; requires human authorization.
* **`BLOCKED`**: Action strictly prohibited by safety invariants (e.g. retry limit reached).
* **`NO_ACTION`**: Opportunity evaluated as unviable for recovery.

---

## 4. Policy Precedence & Conflict Resolution Hierarchy

When observable signals, AI diagnostic opinions, and safety policies interact, the decision engine enforces the following strict hierarchy:

1. **Deterministic Safety Hard Blocks (Highest Priority):**
   * *Exhausted attempts:* If `target_attempt_count >= 3`, proposal is strictly `NO_ACTION` / `BLOCKED`.
   * *Chronic failure:* If customer has $\ge 3$ past payments with $< 25\%$ success rate and an unmitigated decline code, proposal is strictly `NO_ACTION` / `BLOCKED`.
   * *Hard safety blocks always override high-value escalation and AI recommendations.* (e.g. ₹50,000 + 4 failed attempts + AI says recoverable $\rightarrow$ `NO_ACTION` / `BLOCKED`).
2. **High-Value Escalation (Pre-emptive Human Review):**
   * If `amount_minor >= 500000` (₹5,000) and not hard-blocked, proposal is strictly `HUMAN_REVIEW` / `REQUIRES_REVIEW` (`requires_human_approval = True`).
3. **AI Provider Error / Ambiguity Escalation:**
   * If AI diagnosis is unavailable or failure code is `unknown_failure`, proposal routes to `HUMAN_REVIEW`.
4. **Deterministic Domain Routing:**
   * Subscription `past_due` $\rightarrow$ `SUBSCRIPTION_RECOVERY_WORKFLOW`.
   * Expired method $\rightarrow$ `REQUEST_PAYMENT_METHOD_UPDATE`.
   * Insufficient funds $\rightarrow$ `RETRY_LATER` (`cooldown_required = True`).
   * Transient glitch $\rightarrow$ `RETRY_PAYMENT`.
5. **Fallback:**
   * Unclassified decline $\rightarrow$ `NO_ACTION`.

---

## 5. Explanation Chain

Every proposal contains an inspectable `ExplanationChain`:
* `observed_facts`: Factual signals extracted from trusted input.
* `ai_inferences`: Inferences drawn by the Phase 4 AI reasoner.
* `policy_checks`: Deterministic policy checks evaluated.
* `final_rationale`: Human-readable summary of the decision.

---

## 6. Deterministic Proposal ID

Proposal IDs are 100% deterministic across runs:
$$\text{proposal\_id} = \text{uuid5}(\text{NAMESPACE\_DNS}, \text{"recoverai-decision-\{decision\_version\}-\{policy\_version\}-\{target\_type\}-\{target\_id\}"})$$

---

## 7. Frozen Decision Benchmark Reference (`benchmark_decision_v1.json`)

Evaluated on Seed 42 dataset (1,000 Customers, 5,000 Payments, 1,676 Recovery Cases):

* **Evaluated Proposals:** 1,676
* **Action Type Distribution:**
  * `NO_ACTION`: 704
  * `HUMAN_REVIEW`: 268
  * `RETRY_PAYMENT`: 239
  * `RETRY_LATER`: 233
  * `REQUEST_PAYMENT_METHOD_UPDATE`: 201
  * `SUBSCRIPTION_RECOVERY_WORKFLOW`: 31
* **Decision Status Distribution:**
  * `BLOCKED`: 704 (42.00%)
  * `PROPOSED`: 704 (42.00%)
  * `REQUIRES_REVIEW`: 268 (15.99%)
* **Financial Distribution (Paise):**
  * Total Amount at Risk: 531,161,966 paise (~₹5.31M)
  * Proposed Action Amount: 87,385,606 paise (~₹0.87M)
  * Human Review Amount: 261,601,514 paise (~₹2.62M)
  * Blocked Action Amount: 182,174,846 paise (~₹1.82M)
* **Safety Invariant Audit:**
  * Unsafe Action Proposals: **0** (100% policy compliance)
  * Human Review Escalation Rate: 1,599 bps (15.99%)
