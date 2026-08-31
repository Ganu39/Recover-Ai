# Phase 4 — AI Root-Cause Diagnosis

## 1. Objective
Build an AI-powered, read-only root-cause diagnosis service (`DiagnosisAgent`) that analyzes observable customer, transaction, and subscription contexts to produce structured, evidence-grounded failure classifications and qualitative recovery assessments without executing financial actions.

## 2. Scope & Core Requirements
1. **Strict Read-Only AI Reasoning Boundary:**
   - Zero financial execution, zero tool calls, zero Razorpay API dependencies, zero database write operations.
2. **Untrusted Provider Architecture:**
   - `BaseLLMProvider` returns untrusted `RawLLMResponse`.
   - `DiagnosisAgent` parses, validates JSON schema, and constructs the trusted `AIDiagnosisResult`.
   - Execution status tracked explicitly via `DiagnosisStatus` (`SUCCESS`, `PROVIDER_ERROR`, `VALIDATION_ERROR`, `TIMEOUT`).
3. **Money Safety & Integer Minor Units:**
   - Context maintains canonical `amount_minor: int` and `currency: str`, with auxiliary `amount_display: str`.
   - AI never computes financial values.
4. **Strong Evidence Grounding:**
   - Every `EvidenceItem` requires `fact`, `source_field`, and `inference` to ensure strict traceability to observable input.
5. **AI Opinion Scoping:**
   - Output field `ai_recoverability_assessment: Optional[bool]` represents qualitative AI opinion, strictly decoupled from Phase 5 recovery decisions.
6. **Strict Ground-Truth Air-Gap:**
   - `AIDiagnosisInputContext` contains zero evaluation metadata (`is_recoverable`, `scenario_type`, `expected_recovery_reason`).
   - Unit tests enforce absence of ground-truth fields in serialized prompts.
7. **Comprehensive Evaluation Harness:**
   - Evaluator separates Diagnosis Category Accuracy, Recoverability Classification Metrics (in basis points), Evidence Grounding Rate, and Schema Validity Rate.
   - Compares performance against frozen Deterministic Baseline `v1`.
   - `MockLLMProvider` results are strictly labeled as mock infrastructure validation in `benchmark_ai_mock.json`.

## 3. Allowed Changes
* Creating modules in `agents/diagnosis/`.
* Creating automated tests in `tests/test_ai_diagnosis.py`.
* Creating documentation in `docs/ai-diagnosis.md`.
* Updating `README.md`, `docs/PROJECT_CONTEXT.md`, and `docs/CHATGPT_CONTEXT.md`.

## 4. Forbidden Changes
* No live payment execution, retries, or Razorpay API calls.
* No modifying database entities or production tables.
* No publishing mock benchmarks as real AI benchmarks.
* No Phase 5 recovery decision agent logic.

## 5. Acceptance Criteria
1. Provider abstraction isolates untrusted LLM outputs from trusted application state.
2. Strict Pydantic validation handles malformed JSON, timeouts, and schema errors with explicit `DiagnosisStatus`.
3. Context builder produces deterministic, anonymized inputs with canonical field ordering.
4. Ground-truth air-gap is preserved and verified by automated tests.
5. Evaluator compares diagnosis accuracy and recoverability metrics against Baseline `v1`.
6. 100% of automated tests pass across Phase 0, 1, 2, 3, and 4.

## 6. Completion Status
**COMPLETE** (Verified on 2026-08-31 with 73 passing tests, untrusted provider isolation, evidence grounding, and mock validation scorecard docs/benchmark_ai_mock.json).
