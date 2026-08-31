# RecoverAI — AI Root-Cause Diagnosis (Phase 4)

This document provides the architecture, prompt specifications, taxonomy definitions, evidence grounding model, provider abstractions, and evaluation methodology for the **AI Root-Cause Diagnosis** engine built in **Phase 4**.

---

## 1. Engine Purpose & Strict AI Boundary

The AI Root-Cause Diagnosis service (`DiagnosisAgent`) provides read-only analytical reasoning over observable customer payment histories, gateway attempt logs, decline reasons, and subscription states.

### Strict AI Boundaries
* **Read-Only Reasoning:** The AI agent possesses **zero tools**, **zero database write privileges**, and **zero payment execution or retry capabilities**.
* **Decoupled Opinion:** The field `ai_recoverability_assessment: Optional[bool]` represents an analytical AI opinion, strictly decoupled from Phase 5 deterministic recovery decisions.
* **No Razorpay API Calls:** No payment gateway SDKs or live integrations are active.

```text
Observable Data Layer (PostgreSQL / Synthetic ObservableDataset)
        │
        ▼
[ Context Builder (agents/diagnosis/context_builder.py) ]
   ├── Masks identifiers (e.g. cust_...a1b2, pay_...c3d4)
   ├── Formats integer minor units (paise) & human display strings (₹)
   ├── Formats chronological attempt histories & success rates
   └── Strictly excludes hidden ground truth & evaluation metadata
        │
        ▼
[ Prompt Renderer (agents/diagnosis/prompts/v1/) ]
   ├── Immutable system prompt & user context template
   └── Mandates EvidenceItem(fact, source_field, inference)
        │
        ▼
[ Untrusted LLM Provider (agents/diagnosis/providers/) ]
   ├── Returns RawLLMResponse(raw_text, status_code, latency_ms)
   ├── MockLLMProvider (Offline deterministic unit testing & validation)
   └── GenericHTTPLLMProvider (Generic REST adapter for LLM APIs)
        │
        ▼
[ Response Validator & Fallback (agents/diagnosis/service.py) ]
   ├── Parses JSON & validates strictly against AIDiagnosisPayload
   └── Stamped with application-supplied metadata (latency, status, provider)
        │
        ├─────────────────────────────────────────────┐
        ▼ (Downstream Evaluation Harness Only)         ▼ (Strictly Air-Gapped)
[ AI Diagnosis Evaluator (agents/diagnosis/evaluator.py) ] ◄── [ RecoveryGroundTruth ]
   ├── Separates Diagnosis Taxonomy Accuracy from Recoverability Classification
   ├── Evaluates Evidence Grounding & Schema Validity Rates
   └── Compares performance directly against Frozen Deterministic Baseline v1
```

---

## 2. Controlled Diagnosis Taxonomy

The agent classifies failures into a 7-category taxonomy:

1. **`transient_system_error`**: Transient gateway timeout, switch error, or network drop on an otherwise reliable account.
2. **`balance_or_limit_deficit`**: Temporary account balance deficit or transaction card limit reached.
3. **`expired_or_invalid_method`**: Expired payment card, invalid token, or expired mandate.
4. **`persistent_issuer_decline`**: Hard issuer refusal, chronic fraud flag, or exhausted repeated declines ($\ge 3$).
5. **`subscription_billing_issue`**: Recurring billing cycle failure on an active/past_due subscription.
6. **`first_time_user_drop`**: Initial checkout drop-off or friction on a new customer's first payment ($\le 1$ prior transactions).
7. **`insufficient_data`**: Incomplete or ambiguous signals preventing a confident classification (anti-hallucination fallback).

---

## 3. Evidence Grounding & Anti-Hallucination Model

Every evidence point must be represented as a structured `EvidenceItem`:
* **`fact`**: The direct observable signal present in the input context (e.g. `"4 of 4 historical payments succeeded"`).
* **`source_field`**: The exact field name in the input schema (e.g. `"customer_success_count/customer_history_count"`).
* **`inference`**: The logical deduction drawn strictly from that fact (e.g. `"Historical customer intent and reliability are exceptionally high"`).

The AI is explicitly forbidden from inventing bank names, card networks, cardholder geolocation, or user actions not present in the input.

---

## 4. Untrusted Provider Abstraction & Execution Statuses

The provider interface treats the LLM as an untrusted external component:
* `BaseLLMProvider.complete_prompt(...) -> RawLLMResponse`
* Model metadata (`provider_name`, `model_name`, `latency_ms`) is stamped directly by the application adapter, not trusted from LLM-generated text.
* Execution status is tracked explicitly via `DiagnosisStatus`:
  * `SUCCESS`: Response successfully parsed and validated against `AIDiagnosisPayload`.
  * `PROVIDER_ERROR`: Upstream provider returned HTTP error (e.g., 500, 429).
  * `VALIDATION_ERROR`: LLM response contained malformed JSON or violated Pydantic schema constraints.
  * `TIMEOUT`: Request exceeded configured timeout threshold.

---

## 5. Evaluation Harness & Metrics Separation

The `AIDiagnosisEvaluator` evaluates four distinct dimensions:
1. **Execution Integrity:** `schema_validity_rate_bps` and `evidence_grounding_rate_bps`.
2. **Diagnosis Category Accuracy:** Agreement rate between predicted category and underlying scenario archetype.
3. **Recoverability Classification Performance:** True Positives, False Positives, True Negatives, False Negatives, Precision (bps), Recall (bps), F1 Score (bps), and Accuracy (bps).
4. **Comparative Baseline Delta:** Direct delta calculation against frozen Deterministic Baseline `v1` (F1 delta and Revenue Capture Rate delta).

---

## 6. Mock Infrastructure Validation Reference (`benchmark_ai_mock.json`)

* **Benchmark Type:** `MOCK_VALIDATION` (Non-AI Infrastructure Validation)
* **Provider:** `mock_diagnostic_provider` (`mock-simulated-v1`)
* **Prompt Version:** `v1`
* **Evaluated Cases:** 1,676 (Seed 42, 5,000 payments)
* **Schema Validity Rate:** 10,000 bps (100.00%)
* **Evidence Grounding Rate:** 7,649 bps (76.49%)
* **Recoverability Metrics:**
  * Precision: 7,394 bps (73.94%)
  * Recall: 7,676 bps (76.76%)
  * F1 Score: 7,532 bps (75.32%)
* **Delta vs Baseline v1:**
  * Baseline v1 F1: 5,386 bps (53.86%)
  * F1 Score Delta: +2,146 bps (+21.46%)
  * Baseline v1 Capture: 5,015 bps (50.15%)
  * Revenue Capture Delta: +2,210 bps (+22.10%)
