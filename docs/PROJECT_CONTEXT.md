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
2. **Measurable revenue recovery:** Track and prove actual recovered revenue deterministically.
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
[ Synthetic Transaction Engine & Seeder (data/synthetic) ]
   ├── Profiles & Integer Probability Logic (0-9999 bps)
   ├── 8 Canonical Recovery Scenario Archetypes (docs/synthetic-scenarios.md)
   ├── Strict Air-Gapped Evaluation Layer (RecoveryGroundTruth)
   └── Dataset Quality Validator & Minor Units Statistics
        │
        ▼
[ PostgreSQL Database & Alembic Migrations (data/migrations) ]
```

* **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS (`apps/web`).
* **Backend:** FastAPI, Python 3.14, Pydantic Settings, SQLAlchemy 2.0 (`apps/api`).
* **Database & Data Models:** Canonical ORM models in `data/models/`, Alembic migrations in `data/migrations/`.
* **Synthetic Transaction Engine:** Deterministic simulation engine and database seeder in `data/synthetic/`.
* **Agents:** Not implemented (directory placeholder `agents/` ready).
* **Services:** Not implemented (directory placeholder `services/` ready).
* **External Integrations:** None active (Razorpay Test Mode deferred to Phase 7).

## 6. Technology Stack

* **Frontend:** Next.js 14.2+, React 18, TypeScript 5, Tailwind CSS 3.4
* **Backend:** Python 3.14+, FastAPI 0.110+, Uvicorn 0.28+, Pydantic 2.6+, Pydantic Settings 2.2+, Alembic 1.19+
* **Database:** PostgreSQL 16+ (SQLAlchemy 2.0+, asyncpg 0.31+)
* **Synthetic Engine:** Deterministic RNG, integer basis points, evaluation metadata layer
* **Testing:** Pytest 9.1+, HTTPX 0.28+, pytest-asyncio 1.4+
* **Runtime/Tooling:** Node.js v24+, Python venv, Git

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
├── agents/ (.gitkeep)
├── docs/
│   ├── data-model.md
│   ├── synthetic-scenarios.md
│   ├── synthetic-data.md
│   ├── PHASES/
│   │   ├── PHASE_0.md
│   │   ├── PHASE_1.md
│   │   └── PHASE_2.md
│   └── PROJECT_CONTEXT.md
├── services/ (.gitkeep)
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_health.py
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

## 9. Current Phase

* **Phase Number:** Phase 3
* **Phase Name:** Deterministic Revenue-Risk Engine
* **Phase Objective:** Implement deterministic rules, algorithms, and state evaluators to detect revenue at risk from payment failures and subscription past-due events without relying on LLMs.
* **Phase Status:** PLANNED

## 10. Implemented Components

* **Synthetic Transaction Engine (`data/synthetic/`):**
  - `SyntheticDataGenerator`: Deterministic generation pipeline parameterized with random seed, exact customer/payment counts, and reference start timestamps.
  - Behavioral Profiles (`PROFILES`): 5 profiles (`reliable`, `intermittent`, `high_value`, `chronic_failure`, `new_customer`) using 0-9999 bps integer thresholds.
  - Canonical Scenarios (`SCENARIO_SPECS`): 8 archetypes (`high_probability_recoverable`, `low_probability_recoverable`, `clearly_non_recoverable`, `new_customer`, `repeated_failure`, `temporary_failure_after_success_history`, `subscription_failure`, `high_value_payment_failure`).
  - Evaluation Metadata Layer (`RecoveryGroundTruth`): Strict air-gapped ground-truth representations outside production models.
  - Data Quality Validator (`DatasetValidator`): Automated audits verifying foreign keys, non-negative amounts, sequential attempts, and exactly-one recovery targets.
  - Summary Statistics Calculator (`calculate_statistics`): Deterministic reconciliation in integer minor units (paise).
  - PostgreSQL Seeder (`seed_dataset_to_database`): Atomic transaction seeder inserting generated observable entities into PostgreSQL.
  - CLI Tool (`python -m data.synthetic.cli`): Command-line interface for dataset synthesis, validation, and database seeding.
* **Canonical Database Models (`data/models/`):** SQLAlchemy 2.0 ORM models for `Customer`, `Payment`, `PaymentAttempt`, `Subscription`, `RecoveryCase`.
* **Alembic Migration System (`data/migrations/`, `alembic.ini`):** Full async migration framework with initial migration `ed105aca8bfc_0001_initial_entities.py`.
* **FastAPI Backend (`apps/api/main.py`):** FastAPI application with CORS middleware and `GET /health` endpoint returning `{"status": "ok"}`.
* **Configuration Module (`apps/api/core/config.py`):** Pydantic Settings class reading environment variables and `.env`.
* **Database Connection Abstraction (`apps/api/core/database.py`):** Async SQLAlchemy engine (`create_async_engine`) and session factory.
* **Next.js Frontend (`apps/web`):** Next.js 14 App Router application with TypeScript and Tailwind CSS.
* **Automated Test Suite (`tests/`):** 37 automated tests covering health checks, PostgreSQL database constraints, and synthetic engine validation.

## 11. Database State

* **Configuration:** `DATABASE_URL` configured in `apps/api/core/config.py`.
* **Entities:**
  * `Customer`: Merchant customer representation.
  * `Payment`: Commercial payment intent.
  * `PaymentAttempt`: Individual gateway attempts.
  * `Subscription`: Recurring relationship.
  * `RecoveryCase`: Opportunity record.
* **Important Constraints:**
  * Monetary non-negative check: `amount_minor >= 0`, `amount_at_risk_minor >= 0`.
  * Attempt number positive check: `attempt_number > 0`.
  * Unique external IDs: `external_customer_id`, `external_payment_id`, `external_subscription_id`.
  * RecoveryCase Exactly-One Target: `CHECK ((payment_id IS NOT NULL AND subscription_id IS NULL) OR (payment_id IS NULL AND subscription_id IS NOT NULL))`.
  * Controlled enum validation: Database-level CHECK constraints on all status columns.
* **Detailed Documentation:** Refer to [`docs/data-model.md`](data-model.md).

## 12. API State

| Method | Path | Purpose | Status |
| ------ | ---- | ------- | ------ |
| `GET` | `/health` | System health check returning `{"status": "ok"}` | IMPLEMENTED & VERIFIED |

## 13. AI/Agent State

No AI/LLM integration implemented.

## 14. External Integrations

No external integrations implemented.
* Razorpay Test Mode integration is strictly deferred to Phase 7.

## 15. Important Architectural Decisions

### ADR-001 — Monorepo Directory Structure
* **Decision:** Organize the repository into `apps/` (sub-applications `api` and `web`), `agents/` (AI agent logic), `services/` (domain services), `data/` (models/migrations), `tests/`, and `docs/`.
* **Reason:** Provides clear separation of concerns, modularity, and scalability across phases without introducing unnecessary microservices.
* **Date:** 2026-08-31

### ADR-002 — Separation of AI Diagnostics and Financial Execution
* **Decision:** AI agents are restricted to classification, diagnostics, and recovery recommendations. Financial execution and policy enforcement are strictly deterministic.
* **Reason:** Ensures financial safety, regulatory compliance, zero hallucinated transactions, and predictable behavior.
* **Date:** 2026-08-31

### ADR-003 — Asynchronous Database Layer with SQLAlchemy
* **Decision:** Use SQLAlchemy 2.0 with `asyncpg` for PostgreSQL interaction.
* **Reason:** High-throughput async I/O alignment with FastAPI and clean session lifecycle management.
* **Date:** 2026-08-31

### ADR-004 — Integer Minor Units for Monetary Safety
* **Decision:** All monetary columns (`amount_minor`, `amount_at_risk_minor`) strictly use `BigInteger` storing integer minor units (paise/cents) accompanied by non-negative CHECK constraints.
* **Reason:** Completely eliminates floating-point precision/rounding errors in fintech calculations.
* **Date:** 2026-08-31

### ADR-005 — RecoveryCase Target Invariant: Exactly One Target
* **Decision:** `RecoveryCase` enforces a database-level CHECK constraint ensuring it references either a `Payment` OR a `Subscription`, but never both and never neither.
* **Reason:** Guarantees data integrity for recovery workflows without ambiguity about the underlying financial asset.
* **Date:** 2026-08-31

### ADR-006 — Single Canonical Model Location in `data/models/`
* **Decision:** Place all database entity models in `data/models/` as the single canonical location, avoiding duplication in `apps/api/models/`.
* **Reason:** Eliminates model drift and keeps data definition decoupled from API transport layers.
* **Date:** 2026-08-31

### ADR-007 — Integer Basis Points for Synthetic Probabilities
* **Decision:** Represent all synthetic probability thresholds and weights in integer basis points (`0` to `9999` bps) rather than floating-point decimals.
* **Reason:** Ensures deterministic, exact RNG branch execution across different platforms and environments without float rounding drift.
* **Date:** 2026-08-31

### ADR-008 — Strict Air-Gapped Evaluation Layer for Hidden Ground Truth
* **Decision:** Evaluation ground-truth labels (`is_recoverable`, `scenario_type`, `expected_recovery_reason`) are stored exclusively in `RecoveryGroundTruth` evaluation records and are never stored in Phase 1 database tables or exposed in observable API/agent payloads.
* **Reason:** Prevents target leakage and data snooping, forcing downstream AI models to deduce recoverability strictly from observable transaction and historical signals.
* **Date:** 2026-08-31

## 16. Known Limitations

* Live transaction ingestion and recovery processing are not active yet (scheduled for future phases).
* Synthetic engine currently generates simulated data for testing and benchmarking.

## 17. Known Issues

None.

## 18. Future Work

* Phase 3: Deterministic revenue-risk detection engine.
* Phase 4: AI root-cause diagnosis.
* Phase 5: Recovery decision agent.
* Phase 6: Deterministic policy and safety gateway.
* Phase 7: Razorpay Test Mode execution and webhook event processing.
* Phase 8: Audit trail and observability logging.
* Phase 9: Evaluation and recovery metrics calculation.
* Phase 10: Demo UI, hardening, and submission materials.

## 19. Current Phase Acceptance Criteria (Phase 3)

1. Deterministic revenue-risk engine analyzes customer transaction streams and identifies revenue at risk.
2. Generates `RecoveryCase` opportunities deterministically without LLM dependency.
3. Classifies failure urgency, loss magnitude, and retry status.
4. Passes comprehensive automated tests evaluating detection precision against synthetic test datasets.

## 20. Last Verified State

* **Date:** 2026-08-31
* **Automated Tests:** 37/37 tests PASSED in 4.30s (`tests/test_health.py`, `tests/test_database.py`, `tests/test_synthetic.py`).
* **Deterministic Dataset Generation:** Seed 42 produces 100% reproducible dataset (SHA-256: `2423ca5970c24a6a46688bf132256daf4beaf0997c90e9c2b9aacacd6def2fde`).
* **Large-Scale Generation:** 1,000 customers and 5,000 payments generated in 0.263s and validated in 0.033s (0 errors).
* **Database Seeding:** 1,490 synthetic records seeded into PostgreSQL in an atomic transaction without constraint errors.
* **Security Check:** Verified no secrets or `.env` committed.
* **Phase Leakage Check:** Verified no AI/LLM, Razorpay, auth, or Phase 3 recovery engine logic introduced.

## 21. Next Phase

* **Next Phase:** Phase 3 — Deterministic Revenue-Risk Engine
* **Status:** PLANNED
