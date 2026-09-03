# RecoverAI — Project Context

## 1. Project Identity

* **Project Name:** RecoverAI
* **Buildathon:** Razorpay AI Buildathon
* **Selected Track:** AI Revenue Recovery
* **One-Sentence Product Definition:** RecoverAI is an AI-powered revenue recovery platform that detects revenue at risk, diagnoses root causes, estimates recovery probability, and recommends safety-governed recovery interventions executed deterministically through payment gateways.

## 2. Product Goal

RecoverAI automatically detects, diagnoses, and recovers revenue lost to payment failures, checkout abandonment, and subscription billing issues. It combines AI-driven diagnostics with deterministic financial execution to maximize merchant recovery rates while guaranteeing policy compliance and complete auditability.

## 3. Core User Problem

Online merchants lose significant revenue to:
* Failed one-off checkout transactions (network glitches, insufficient funds, card declines).
* Involuntary subscription churn (expired cards, recurring billing failures).
* High-intent checkout abandonment.

Merchants lack automated, intelligent, and safe recovery workflows that analyze why a failure occurred and trigger the most effective recovery action without risking customer trust or financial integrity.

## 4. Product Principles

1. **Working product over feature quantity:** Build solid, verifiable foundations phase-by-phase.
2. **Measurable revenue recovery:** Track and prove actual recovered revenue deterministically against the frozen baseline.
3. **AI reasoning separated from financial execution:** The LLM diagnoses and recommends; deterministic rules and code execute financial actions.
4. **Deterministic safety controls:** No automated action executes without passing strict policy gateways.
5. **Auditable actions:** Every diagnosis, recommendation, policy evaluation, and execution is recorded in an immutable audit trail.
6. **Graceful failure:** System degrades safely when external services or AI components fail.
7. **Test Mode during development:** Use Razorpay Test Mode only; never use live financial credentials during development.
8. **No fabricated metrics:** Never invent test results, APIs, or recovery numbers.

## 5. Current Architecture

```text
[ Browser / Client ]
        │
        ▼
[ Next.js Frontend (apps/web) ]
        │ (HTTP/JSON)
        ▼
[ FastAPI Backend (apps/api) ]
   ├── Core Config (Pydantic Settings)
   ├── Database Abstraction (SQLAlchemy Async Engine & Session)
   └── Endpoints (/health)
        │
        ▼
[ Canonical Data Model (data/models) ]
   ├── Customer (customers)
   ├── Payment (payments)
   ├── PaymentAttempt (payment_attempts)
   ├── Subscription (subscriptions)
   └── RecoveryCase (recovery_cases)
        │
        ├─────────────────────────────────────────────┐
        ▼                                             ▼
[ Deterministic Risk Engine ]             [ AI Root-Cause Diagnosis ]
(services/risk_engine - Baseline v1)     (agents/diagnosis - v1)
   ├── Feature Context Extractor            ├── Sanitized Context Builder
   ├── Deterministic Rules & Reasons        ├── Untrusted Provider Layer
   ├── Baseline Evaluation Harness          ├── Pydantic Response Validator
   └── Minor Units & Basis Points           └── Comparative AI Evaluator
        │                                             │
        └──────────────────────┬──────────────────────┘
                               │
                               ▼
[ Recovery Decision Agent (agents/decision - v1 / Policy v1) ]
   ├── Deterministic Safety Hard Blocks (Attempt >= 3, Chronic decline)
   ├── High-Value Pre-emptive Escalation (Amount >= ₹5,000)
   ├── Domain Routing (Subscription workflow, Expired card, Cooldown retry)
   └── Structured Explanation Chain & Deterministic Proposal IDs
        │
        ▼
[ Deterministic Policy & Safety Gateway (agents/gateway - v1 / Policy v1) ]
   ├── 12-Stage Safety Check Pipeline (Kill Switch, Version, Identity, Integrity)
   ├── In-Memory Idempotency & Replay Protection (Zero Duplicate Execution)
   ├── Sliding-Window Safety Rate Limiting & Fail-Closed Kill Switch
   └── Terminal Authorization (APPROVED, BLOCKED, REQUIRES_REVIEW, etc.)
        │
        ▼
[ Bounded Recovery Execution Layer (services/execution - v1) ]
   ├── Pre-Execution Authorization Re-validation
   ├── Deterministic Execution Idempotency & In-Flight Concurrency Protection
   ├── Provider Adapter Abstraction (Mock simulation & Razorpay Test Mode rzp_test_)
   ├── Execution State Machine (AUTHORIZED -> PROVIDER_REQUESTED -> SUCCEEDED / UNKNOWN)
   ├── HMAC-SHA256 Webhook Verification & State Reconciliation
   └── Immutable Execution Audit Logger & Revenue Recovery Metrics
        │
        ▼
[ Synthetic Transaction Engine & Seeder (data/synthetic) ]
   ├── Profiles & Integer Probability Logic (0-9999 bps)
   ├── 8 Canonical Recovery Scenario Archetypes (docs/synthetic-scenarios.md)
   ├── Air-Gapped Evaluation Layer (RecoveryGroundTruth)
   └── Dataset Quality Validator & Minor Units Statistics
        │
        ▼
[ PostgreSQL Database & Alembic Migrations (data/migrations) ]
```

## 6. Technology Stack

* **Frontend:** Next.js 14.2+, React 18, TypeScript 5, Tailwind CSS 3.4
* **Backend:** Python 3.14+, FastAPI 0.110+, Uvicorn 0.28+, Pydantic 2.6+, Pydantic Settings 2.2+, Alembic 1.19+
* **Database:** PostgreSQL 16+ (SQLAlchemy 2.0+, asyncpg 0.31+)
* **Synthetic Engine:** Deterministic RNG, integer basis points, evaluation metadata layer
* **Risk Engine:** Deterministic rule-based baseline (`v1`), air-gapped evaluation harness, basis-point metrics
* **AI Diagnosis Engine:** Read-only analytical reasoner (`v1`), provider abstraction (`MockLLMProvider`, `GenericHTTPLLMProvider`), evidence grounding, Pydantic schema validation
* **Recovery Decision Agent:** Policy-first recommendation engine (`v1`/`v1`), deterministic proposal IDs, strict safety hard blocks, human-review escalation
* **Safety Gateway:** Deterministic policy gatekeeper (`v1`/`v1`), 12-stage safety check pipeline, executable action allowlist, fail-closed kill switch, in-memory idempotency & rate limiting
* **Execution Layer:** Bounded recovery executor (`v1`), provider adapter (`BasePaymentProvider`, `MockPaymentProvider`, `RazorpayTestProvider`), deterministic UUID5 idempotency, execution state machine, HMAC webhook verification, state reconciliation
* **Testing:** Pytest 9.1+, HTTPX 0.28+, pytest-asyncio 1.4+

## 7. Repository Structure

```text
recover-ai/
├── apps/
│   ├── api/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── requirements.txt
│   └── web/
│       ├── app/
│       │   ├── globals.css
│       │   ├── layout.tsx
│       │   └── page.tsx
│       ├── next.config.mjs
│       ├── package.json
│       ├── postcss.config.js
│       ├── tailwind.config.ts
│       └── tsconfig.json
├── data/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── customer.py
│   │   ├── enums.py
│   │   ├── payment.py
│   │   ├── recovery_case.py
│   │   └── subscription.py
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── ed105aca8bfc_0001_initial_entities.py
│   └── synthetic/
│       ├── __init__.py
│       ├── cli.py
│       ├── generator.py
│       ├── models.py
│       ├── profiles.py
│       ├── scenarios.py
│       ├── seeder.py
│       ├── statistics.py
│       └── validator.py
├── services/
│   └── risk_engine/
│       ├── __init__.py
│       ├── cli.py
│       ├── engine.py
│       ├── evaluator.py
│       ├── extractor.py
│       ├── metrics.py
│       ├── models.py
│       └── rules.py
├── agents/
│   ├── diagnosis/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── context_builder.py
│   │   ├── evaluator.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── prompts/
│   │   │   └── v1/
│   │   │       ├── system_prompt.md
│   │   │       └── user_template.md
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── http_provider.py
│   │       └── mock.py
│   └── decision/
│       ├── __init__.py
│       ├── cli.py
│       ├── evaluator.py
│       ├── policy.py
│       ├── schemas.py
│       └── service.py
├── docs/
│   ├── data-model.md
│   ├── synthetic-scenarios.md
│   ├── synthetic-data.md
│   ├── risk-engine.md
│   ├── ai-diagnosis.md
│   ├── recovery-decision.md
│   ├── benchmark_v1.json
│   ├── benchmark_ai_mock.json
│   ├── benchmark_decision_v1.json
│   ├── CHATGPT_CONTEXT.md
│   ├── PHASES/
│   │   ├── PHASE_0.md
│   │   ├── PHASE_1.md
│   │   ├── PHASE_2.md
│   │   ├── PHASE_3.md
│   │   ├── PHASE_4.md
│   │   └── PHASE_5.md
│   └── PROJECT_CONTEXT.md
├── tests/
│   ├── __init__.py
│   ├── test_ai_diagnosis.py
│   ├── test_database.py
│   ├── test_health.py
│   ├── test_recovery_decision.py
│   ├── test_risk_engine.py
│   └── test_synthetic.py
├── .env.example
├── .gitignore
├── AGENTS.md
├── alembic.ini
└── README.md
```

## 8. Completed Phases

| Phase | Status | Date | Summary |
| ----- | ------ | ---- | ------- |
| Phase 0 — Foundation & Engineering Rules | COMPLETE | 2026-08-31 | Established repository layout, FastAPI `/health`, Next.js frontend placeholder, database connection abstraction, automated pytest suite, `.env.example`, `AGENTS.md`, and `README.md`. |
| Phase 1 — Database & Data Model | COMPLETE | 2026-08-31 | Established canonical PostgreSQL data models (`Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase`), Alembic migration framework, integer minor units money safety, exactly-one target constraint, and comprehensive PostgreSQL test suite (19 passing tests). |
| Phase 2 — Synthetic Transaction Engine | COMPLETE | 2026-08-31 | Built 100% deterministic synthetic transaction generator, 5 behavioral profiles, 8 canonical scenario archetypes, integer probability logic, strictly air-gapped evaluation metadata layer, data quality validator, integer minor unit statistics, and PostgreSQL seeder. Verified with 37 passing automated tests and 5,000-payment dataset. |
| Phase 3 — Deterministic Revenue-Risk Engine | COMPLETE | 2026-08-31 | Built non-AI deterministic revenue-risk evaluation engine (Baseline `v1`), distinct reason codes, decoupled recoverability from financial exposure, air-gapped evaluation harness, basis-point metrics, and frozen benchmark scorecard (`docs/benchmark_v1.json`). 53 automated tests passing. |
| Phase 4 — AI Root-Cause Diagnosis | COMPLETE | 2026-08-31 | Built read-only AI root-cause diagnostic engine (`v1`), untrusted provider abstraction (`BaseLLMProvider`, `MockLLMProvider`, `GenericHTTPLLMProvider`), strict Pydantic response validation, structured evidence grounding (`EvidenceItem`), AI-opinion scoping, air-gapped evaluation harness, and mock validation scorecard (`docs/benchmark_ai_mock.json`). 73 automated tests passing. |
| Phase 5 — Recovery Decision Agent | COMPLETE | 2026-08-31 | Built policy-first recovery decision agent (`v1`/`v1`), 6-action recovery taxonomy, deterministic proposal UUIDs (`uuid5`), strict policy precedence hierarchy (Hard Blocks > High-Value > Routing > AI), inspectable explanation chains, human-review escalation, and published decision benchmark scorecard (`docs/benchmark_decision_v1.json`). 100 automated tests passing. |

## 9. Current Phase

* **Phase Number:** Phase 6
* **Phase Name:** Deterministic Policy & Safety Gateway
* **Phase Objective:** Implement the deterministic policy gateway that validates recovery decision proposals against merchant policies, daily recovery limits, customer communication quotas, and gateway velocity rules before permitting execution.
* **Phase Status:** PLANNED

## 10. Implemented Components

* **Recovery Decision Agent (`agents/decision/` - Version `v1`, Policy `v1`):**
  - `RecoveryDecisionAgent`: Synthesizes policy-governed decision proposals.
  - Precedence Hierarchy: Deterministic safety hard blocks strictly override high-value escalation and AI recommendations.
  - Action Taxonomy (`RecoveryActionType`): `NO_ACTION`, `RETRY_PAYMENT`, `RETRY_LATER`, `REQUEST_PAYMENT_METHOD_UPDATE`, `SUBSCRIPTION_RECOVERY_WORKFLOW`, `HUMAN_REVIEW`.
  - Proposal Status (`DecisionStatus`): `PROPOSED`, `REQUIRES_REVIEW`, `BLOCKED`, `NO_ACTION`.
  - `derive_deterministic_proposal_id`: 100% deterministic UUID generation using `uuid5`.
  - `RecoveryDecisionEvaluator`: Evaluates proposals against ground truth, verifies zero unsafe proposals, and outputs `docs/benchmark_decision_v1.json`.
* **AI Root-Cause Diagnosis (`agents/diagnosis/` - Version `v1`):**
  - `AIDiagnosisContextBuilder`, `DiagnosisAgent`, `MockLLMProvider`, `GenericHTTPLLMProvider`, `AIDiagnosisEvaluator`.
* **Deterministic Revenue-Risk Engine (`services/risk_engine/` - Baseline `v1`):**
  - `ObservableFeatureExtractor`, `DeterministicRiskEngine`, `BaselineEvaluator`, `calculate_evaluation_metrics`.
* **Synthetic Transaction Engine (`data/synthetic/`):**
  - `SyntheticDataGenerator`, `DatasetValidator`, `calculate_statistics`, `seed_dataset_to_database`.
* **Canonical Database Models (`data/models/`):**
  - SQLAlchemy 2.0 ORM models for `Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase`.
* **Alembic Migration System (`data/migrations/`):** Initial migration `ed105aca8bfc_0001_initial_entities.py`.
* **FastAPI Backend (`apps/api/`):** FastAPI application with CORS middleware and `GET /health` endpoint.
* **Automated Test Suite (`tests/`):** 100 automated tests passing across health, database, synthetic, risk engine, AI diagnosis, and decision modules.

## 11. Database State

* **Configuration:** `DATABASE_URL` configured in `apps/api/core/config.py`.
* **Entities:** `Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase`.
* **Important Constraints:**
  * Monetary non-negative check: `amount_minor >= 0`, `amount_at_risk_minor >= 0`.
  * Attempt number positive check: `attempt_number > 0`.
  * Unique external IDs: `external_customer_id`, `external_payment_id`, `external_subscription_id`.
  * RecoveryCase Exactly-One Target: `CHECK ((payment_id IS NOT NULL AND subscription_id IS NULL) OR (payment_id IS NULL AND subscription_id IS NOT NULL))`.

## 12. API State

| Method | Path | Purpose | Status |
| ------ | ---- | ------- | ------ |
| `GET` | `/health` | System health check returning `{"status": "ok"}` | IMPLEMENTED & VERIFIED |

## 13. AI/Agent State

* **Diagnosis Agent (`agents/diagnosis/`):** Read-only root-cause diagnostic reasoner. Zero write tools, zero payment access.
* **Recovery Decision Agent (`agents/decision/`):** Policy-first recommendation agent. Produces decision proposals only. Zero execution capabilities.

## 14. External Integrations

No external payment integrations active.
* Razorpay Test Mode integration is strictly deferred to Phase 7.

## 15. Important Architectural Decisions

### ADR-001 — Monorepo Directory Structure
* **Decision:** Organize into `apps/`, `agents/`, `services/`, `data/`, `tests/`, and `docs/`.
* **Date:** 2026-08-31

### ADR-002 — Separation of AI Diagnostics and Financial Execution
* **Decision:** AI agents diagnose and recommend; deterministic rules execute financial actions.
* **Date:** 2026-08-31

### ADR-003 — Asynchronous Database Layer with SQLAlchemy
* **Decision:** Use SQLAlchemy 2.0 with `asyncpg` for PostgreSQL interaction.
* **Date:** 2026-08-31

### ADR-004 — Integer Minor Units for Monetary Safety
* **Decision:** All monetary values use `BigInteger` storing integer minor units (paise) with non-negative constraints.
* **Date:** 2026-08-31

### ADR-005 — RecoveryCase Target Invariant: Exactly One Target
* **Decision:** `RecoveryCase` enforces `CHECK ((payment_id IS NOT NULL AND subscription_id IS NULL) OR (payment_id IS NULL AND subscription_id IS NOT NULL))`.
* **Date:** 2026-08-31

### ADR-006 — Single Canonical Model Location in `data/models/`
* **Decision:** Place all entity models in `data/models/`.
* **Date:** 2026-08-31

### ADR-007 — Integer Basis Points for Synthetic Probabilities
* **Decision:** Represent all synthetic probability thresholds and weights in integer basis points (`0` to `9999` bps).
* **Date:** 2026-08-31

### ADR-008 — Strict Air-Gapped Evaluation Layer for Hidden Ground Truth
* **Decision:** Evaluation ground-truth labels are stored exclusively in `RecoveryGroundTruth` evaluation records outside database entities and observable feature contexts.
* **Date:** 2026-08-31

### ADR-009 — Decoupled Recoverability from Financial Exposure Priority
* **Decision:** `predicted_recoverable` (Boolean) and `risk_level` (Enum) are evaluated as separate dimensions.
* **Date:** 2026-08-31

### ADR-010 — Frozen Baseline Benchmark Versioning
* **Decision:** The deterministic baseline is explicitly tagged as `v1` and frozen (`docs/benchmark_v1.json`).
* **Date:** 2026-08-31

### ADR-011 — Untrusted Provider Boundary & Strict Schema Validation
* **Decision:** Providers return untrusted `RawLLMResponse`; `DiagnosisAgent` parses, validates via Pydantic (`AIDiagnosisPayload`), and produces trusted `AIDiagnosisResult`.
* **Date:** 2026-08-31

### ADR-012 — Traceable Evidence Grounding & AI Scoped Opinions
* **Decision:** Every evidence deduction requires `EvidenceItem(fact, source_field, inference)`. Field `ai_recoverability_assessment` is scoped strictly as qualitative analytical opinion.
* **Date:** 2026-08-31

### ADR-013 — Deterministic Safety Hard Blocks & Precedence Hierarchy
* **Decision:** In the Recovery Decision Agent, deterministic safety hard blocks (attempts $\ge 3$, chronic decline) have highest precedence and strictly override high-value escalation and AI recommendations.
* **Date:** 2026-08-31

### ADR-014 — Deterministic Proposal Identity & Zero-Execution Boundary
* **Decision:** Proposal IDs are 100% deterministic using `uuid5`. Decision proposals represent recommendation records only and contain zero execution capabilities or boolean execution triggers.
* **Date:** 2026-08-31

### ADR-015 — Deterministic Policy & Safety Gateway Boundary
* **Decision:** Phase 6 implements the final non-execution safety gateway (`DeterministicSafetyGateway`, `gateway_version = "v1"`, `policy_version = "v1"`). It enforces a 12-stage safety pipeline, executable action allowlist, independent attempt cap defense-in-depth, fail-closed kill switch, in-memory idempotency & replay protection, sliding-window rate limiting, and integer minor-unit financial integrity. `eligible_for_execution_layer = True` indicates gateway approval only and never triggers payment execution.
* **Date:** 2026-09-03

### ADR-016 — Bounded Recovery Execution Layer & Test-Mode Isolation
* **Decision:** Phase 7 implements the bounded execution layer (`ExecutionService`, `v1`). Executes only Phase 6-approved proposals, revalidates authorization before dispatch, isolates Razorpay behind `BasePaymentProvider` (`RazorpayTestProvider`), enforces strict Test Mode (`rzp_test_...` key pattern only, failing closed on live mode or live keys), enforces deterministic execution idempotency (`uuid5`), handles transport timeouts as `UNKNOWN_PROVIDER_STATE` without blind duplicate execution, verifies HMAC-SHA256 webhook signatures, performs state reconciliation, and emits immutable execution audit records with zero secret leakage.
* **Date:** 2026-09-03

### ADR-017 — Production-Quality Operations Frontend & Stitch MCP Architecture
* **Decision:** Buildathon frontend implemented as a Next.js 14 application in `apps/web/` designed with Stitch MCP. Exposes 4 top-level views (Command Center Dashboard, Recovery Cases Directory, Safeguards & Governance Matrix, and Analytics Ledger), a 6-stage visual pipeline funnel, 4-flow judge demo bar, and an end-to-end 7-stage case investigation modal. Integrates with FastAPI read-only endpoints (`/api/v1/overview`, `/api/v1/cases`, `/api/v1/cases/{id}`, `/api/v1/safeguards`, `/api/v1/analytics`) and provides transparent fallback to the canonical Seed 42 frozen benchmark cache.
* **Date:** 2026-09-03

## 16. Frozen Benchmark References

* **Baseline Risk Engine (`v1`):** Precision = 74.25%, Recall = 42.26%, F1 = 53.86%, Capture Rate = 50.15% ([docs/benchmark_v1.json](docs/benchmark_v1.json)).
* **Mock AI Diagnosis (`v1`):** Precision = 73.94%, Recall = 76.76%, F1 = 75.32%, Capture Rate = 72.25% ([docs/benchmark_ai_mock.json](docs/benchmark_ai_mock.json)).
* **Recovery Decision Proposals (`v1`/`v1`):** Total Evaluated = 1,676, Proposed = 704 (42.00%), Blocked = 704 (42.00%), Requires Review = 268 (15.99%), Unsafe Proposals = 0 ([docs/benchmark_decision_v1.json](docs/benchmark_decision_v1.json)).
* **Safety Gateway Benchmark (`v1`/`v1`):** Total Evaluated = 1,676, Approved = 689 (41.10%), Blocked = 719 (42.89%), Requires Review = 268 (15.99%), Rate Limited = 0, Kill Switch = 0, Unsafe Authorizations = 0 (0 bps), Financial Violations = 0 ([docs/benchmark_gateway_v1.json](docs/benchmark_gateway_v1.json)).
* **Execution Layer Benchmark (`v1`):** Total Proposals Received = 1,676, Phase 6 Authorized = 689, Executions Attempted = 456 (56,195,598 paise), Executions Deferred (Cooldown) = 233 (29,064,137 paise), Confirmed Recovered Revenue = 56,195,598 paise (~₹561.9k), Unauthorized Execution Rate = 0 bps, Duplicate Execution Rate = 0 bps, Financial Violation Rate = 0 bps ([docs/benchmark_execution_v1.json](docs/benchmark_execution_v1.json)).

## 17. Last Verified State

* **Date:** 2026-09-03
* **Automated Tests:** 184 tests PASSED in 1.93s across Phases 0–7 and API endpoints (`tests/test_health.py`, `tests/test_synthetic.py`, `tests/test_risk_engine.py`, `tests/test_ai_diagnosis.py`, `tests/test_recovery_decision.py`, `tests/test_safety_gateway.py`, `tests/test_execution_layer.py`, `tests/test_api_endpoints.py`).
* **Frontend Verification:** `npm run type-check` PASSED (0 errors), `npm run lint` PASSED (0 warnings/errors), `npm run build` PASSED (100% static production prerendering).
* **Security & Boundary Verification:** Live Razorpay execution strictly prohibited and fails closed; Razorpay imports isolated strictly to `services/execution/razorpay_provider.py`; zero AI execution bypass; zero floating-point monetary arithmetic; 0 bps unauthorized execution rate; 0 bps duplicate execution rate.

## 18. Project Status

* **Status:** ALL PLANNED PHASES (Phase 0 through Phase 7) COMPLETE.
* **Frontend/Productization:** COMPLETE (Next.js 14 Command Center + Stitch MCP design).
* **Phase 8:** NONE (Strictly no Phase 8).
