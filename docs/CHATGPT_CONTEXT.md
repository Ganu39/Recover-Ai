# RecoverAI — ChatGPT Technical Reviewer Context

## Product & Architectural State Summary (Phases 0 - 4 COMPLETE)

### 1. Core Principles & Safety Model
* **Separation of Reasoning vs Financial Execution:** LLM agents (Phase 4 diagnosis, Phase 5 recovery recommendations) are read-only reasoners. All financial execution and safety checks are deterministic (Phase 6, Phase 7).
* **Integer Minor Currency Units:** All monetary quantities use integer paise (`amount_minor`, `amount_at_risk_minor`). Zero floating-point arithmetic.
* **Basis Points for Probabilities & Metrics:** All probabilities and evaluation scores use integer basis points (0–10000 bps).
* **Air-Gapped Evaluation Layer:** Ground-truth labels (`RecoveryGroundTruth`) are strictly decoupled from observable context and database schemas.

### 2. Completed Phases Overview
* **Phase 0 (Foundation):** Root architecture, Next.js web app, FastAPI `/health`, PostgreSQL connection abstraction, testing framework.
* **Phase 1 (Data Foundation):** Canonical PostgreSQL schema (`Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase` with exactly-one target constraint), Alembic migrations.
* **Phase 2 (Synthetic Transaction Engine):** Deterministic simulation engine, 5 behavioral customer profiles, 8 canonical scenario archetypes, integer minor units statistics, PostgreSQL seeder.
* **Phase 3 (Deterministic Revenue-Risk Engine):** Non-AI baseline (`v1`), distinct reason codes, decoupled recoverability from financial exposure, air-gapped evaluation harness, frozen benchmark (`docs/benchmark_v1.json`: F1 = 53.86%, Revenue Capture Rate = 50.15%).
* **Phase 4 (AI Root-Cause Diagnosis):** Read-only AI diagnostic reasoner (`v1`), 7-category taxonomy, untrusted provider abstraction (`BaseLLMProvider`, `MockLLMProvider`, `GenericHTTPLLMProvider`), strict Pydantic parsing (`AIDiagnosisPayload` -> `AIDiagnosisResult`), structured evidence grounding (`EvidenceItem`), qualitative confidence, explicit execution statuses (`SUCCESS`, `PROVIDER_ERROR`, `VALIDATION_ERROR`, `TIMEOUT`), mock validation scorecard (`docs/benchmark_ai_mock.json`).

### 3. Active Status & Next Phase
* **Active Status:** Phase 4 COMPLETE (73 passing tests).
* **Next Phase:** Phase 5 — Recovery Decision Agent (PLANNED).
