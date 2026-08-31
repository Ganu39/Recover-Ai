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
        ▼
[ Deterministic Revenue-Risk Engine (services/risk_engine - Baseline v1) ]
   ├── Observable Feature Extractor (extractor.py)
   ├── Deterministic Rules & Reason Codes (rules.py)
   ├── Risk Evaluation Engine (engine.py)
   ├── Air-Gapped Baseline Evaluator (evaluator.py)
   └── Minor Units & Basis Points Metrics (metrics.py)
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
├── agents/ (.gitkeep)
├── docs/
│   ├── data-model.md
│   ├── synthetic-scenarios.md
│   ├── synthetic-data.md
│   ├── risk-engine.md
│   ├── benchmark_v1.json
│   ├── PHASES/
│   │   ├── PHASE_0.md
│   │   ├── PHASE_1.md
│   │   ├── PHASE_2.md
│   │   └── PHASE_3.md
│   └── PROJECT_CONTEXT.md
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_health.py
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

## 9. Current Phase

* **Phase Number:** Phase 4
* **Phase Name:** AI Root-Cause Diagnosis
* **Phase Objective:** Build the AI-driven root cause diagnostic service that analyzes failed payment contexts, generates structured diagnostic explanations, and estimates recovery probability to outperform the Phase 3 baseline.
* **Phase Status:** PLANNED

## 10. Implemented Components

* **Deterministic Revenue-Risk Engine (`services/risk_engine/` - Baseline `v1`):**
  - `ObservableFeatureExtractor`: Extracts customer tenure, attempt counts, decline codes, and historical success rates from observable entities.
  - `DeterministicRiskEngine`: Evaluates `ObservableRiskContext` against frozen `v1` ruleset and outputs `RiskEvaluationResult`.
  - Reason Codes (`RiskReasonCode`): `RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS`, `RC_CHRONIC_DECLINE_HISTORY`, `RC_TRANSIENT_FAILURE_PROVEN_HISTORY`, `RC_INSUFFICIENT_FUNDS`, `RC_SUBSCRIPTION_BILLING_GLITCH`, `RC_FIRST_TIME_CHECKOUT_DROP`, `RC_HIGH_VALUE_EXPOSURE`, `RC_UNRESOLVED_HARD_DECLINE`.
  - `BaselineEvaluator`: Downstream evaluation pipeline comparing risk engine predictions against air-gapped `RecoveryGroundTruth` via deterministic target matching.
  - `calculate_evaluation_metrics`: Integer basis points (precision, recall, F1, accuracy, capture rate) and minor units monetary metrics.
  - Benchmark CLI (`python -m services.risk_engine.cli`): Command-line benchmark generator publishing `docs/benchmark_v1.json`.
* **Synthetic Transaction Engine (`data/synthetic/`):**
  - `SyntheticDataGenerator`, `DatasetValidator`, `calculate_statistics`, `seed_dataset_to_database`.
* **Canonical Database Models (`data/models/`):**
  - SQLAlchemy 2.0 ORM models for `Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase`.
* **Alembic Migration System (`data/migrations/`):** Initial migration `ed105aca8bfc_0001_initial_entities.py`.
* **FastAPI Backend (`apps/api/`):** FastAPI application with CORS middleware and `GET /health` endpoint.
* **Automated Test Suite (`tests/`):** 53 automated tests passing across health, database, synthetic, and risk engine modules.

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

No AI/LLM integration implemented yet. Scheduled for Phase 4.

## 14. External Integrations

No external integrations implemented.
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
* **Decision:** Evaluation ground-truth labels (`is_recoverable`, `scenario_type`, `expected_recovery_reason`) are stored exclusively in `RecoveryGroundTruth` evaluation records outside database entities and observable feature contexts.
* **Date:** 2026-08-31

### ADR-009 — Decoupled Recoverability from Financial Exposure Priority
* **Decision:** `predicted_recoverable` (Boolean) and `risk_level` (Enum) are evaluated as separate dimensions. High-value transactions attach exposure evidence without forcing recoverability on chronic failure accounts.
* **Date:** 2026-08-31

### ADR-010 — Frozen Baseline Benchmark Versioning
* **Decision:** The deterministic baseline is explicitly tagged as `v1` and frozen. Benchmark results (`docs/benchmark_v1.json`) serve as the empirical performance reference for future AI phases without post-hoc rule tuning.
* **Date:** 2026-08-31

## 16. Frozen Baseline Benchmark Reference (`v1` — Seed 42, 5,000 Payments)

* **Evaluated Cases:** 1,676
* **Confusion Matrix:** TP = 522, FP = 181, TN = 260, FN = 713
* **Precision:** 7,425 bps (74.25%)
* **Recall:** 4,226 bps (42.26%)
* **F1 Score:** 5,386 bps (53.86%)
* **Accuracy:** 4,665 bps (46.65%)
* **Total Amount at Risk:** 531,161,966 paise (~₹5.31M)
* **Recoverable Amount Captured (TP):** 196,495,127 paise (~₹1.96M)
* **Recoverable Amount Missed (FN):** 195,308,536 paise (~₹1.95M)
* **False Intervention Amount (FP):** 61,971,831 paise (~₹0.62M)
* **Revenue Capture Rate:** 5,015 bps (50.15%)

## 17. Last Verified State

* **Date:** 2026-08-31
* **Automated Tests:** 53/53 tests PASSED in 7.59s (`tests/test_health.py`, `tests/test_database.py`, `tests/test_synthetic.py`, `tests/test_risk_engine.py`).
* **Frozen Benchmark:** Published `docs/benchmark_v1.json` and documented in `docs/risk-engine.md`.
* **Security & Leakage Check:** Zero LLM/AI dependencies, zero Razorpay API dependencies, zero floating-point arithmetic.

## 18. Next Phase

* **Next Phase:** Phase 4 — AI Root-Cause Diagnosis
* **Status:** PLANNED
