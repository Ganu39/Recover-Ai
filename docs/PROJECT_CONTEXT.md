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
[ PostgreSQL Database (Connection abstraction ready; schema in Phase 1) ]
```

* **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS (`apps/web`).
* **Backend:** FastAPI, Python 3.14, Pydantic Settings (`apps/api`).
* **Database:** PostgreSQL connection and session abstraction via SQLAlchemy `create_async_engine` (`apps/api/core/database.py`).
* **Agents:** Not implemented (directory placeholder `agents/` ready).
* **Services:** Not implemented (directory placeholder `services/` ready).
* **External Integrations:** None active (Razorpay Test Mode deferred to Phase 7).

## 6. Technology Stack

* **Frontend:** Next.js 14.2+, React 18, TypeScript 5, Tailwind CSS 3.4
* **Backend:** Python 3.14+, FastAPI 0.110+, Uvicorn 0.28+, Pydantic 2.6+, Pydantic Settings 2.2+
* **Database:** PostgreSQL (SQLAlchemy 2.0+, asyncpg 0.31+)
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
├── agents/ (.gitkeep)
├── data/ (.gitkeep)
├── docs/
│   ├── PHASES/
│   └── PROJECT_CONTEXT.md
├── services/ (.gitkeep)
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

## 8. Completed Phases

| Phase | Status | Date | Summary |
| ----- | ------ | ---- | ------- |
| Phase 0 — Foundation & Engineering Rules | COMPLETE | 2026-08-31 | Established repository layout, FastAPI `/health`, Next.js frontend placeholder, database connection abstraction, automated pytest suite, `.env.example`, `AGENTS.md`, and `README.md`. |

## 9. Current Phase

* **Phase Number:** Phase 1
* **Phase Name:** Database & Data Model
* **Phase Objective:** Design and implement PostgreSQL data models, relational schemas, constraints, and migrations for transactions, recovery events, safety policies, and audit logs.
* **Phase Status:** IN PROGRESS

## 10. Implemented Components

* **FastAPI Backend (`apps/api/main.py`):** FastAPI application with CORS middleware and `GET /health` endpoint returning `{"status": "ok"}`.
* **Configuration Module (`apps/api/core/config.py`):** Pydantic Settings class reading environment variables and `.env`.
* **Database Connection Abstraction (`apps/api/core/database.py`):** Async SQLAlchemy engine (`create_async_engine`) and session factory (`async_sessionmaker`, `get_db_session`).
* **Next.js Frontend (`apps/web`):** Next.js 14 App Router application with TypeScript and Tailwind CSS displaying placeholder system status.
* **Automated Test Suite (`tests/test_health.py`):** Pytest test case testing API startup and `GET /health` response.

## 11. Database State

* **Configuration:** `DATABASE_URL` configured in `apps/api/core/config.py` (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/recoverai`).
* **Engine & Sessions:** SQLAlchemy async engine and session factory created in `apps/api/core/database.py`.
* **Entities & Tables:** None created yet. Entity models and migrations are deferred to Phase 1.
* **Migrations:** None created yet.

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

## 16. Known Limitations

* Database connection abstraction is established, but tables and schemas do not exist yet (scheduled for Phase 1).
* Frontend currently only displays a basic status placeholder without real-time API polling.

## 17. Known Issues

None.

## 18. Future Work

* Phase 1: Database schemas and data models (Transactions, Failures, Recovery Actions, Policy Rules, Audit Logs).
* Phase 2: Synthetic transaction generator for testing failure scenarios.
* Phase 3: Deterministic revenue-risk detection engine.
* Phase 4: AI root-cause diagnosis.
* Phase 5: Recovery decision agent.
* Phase 6: Deterministic policy and safety gateway.
* Phase 7: Razorpay Test Mode execution and webhook event processing.
* Phase 8: Audit trail and observability logging.
* Phase 9: Evaluation and recovery metrics calculation.
* Phase 10: Demo UI, hardening, and submission materials.

## 19. Current Phase Acceptance Criteria (Phase 1)

1. PostgreSQL entity models defined with explicit typed structures and constraints.
2. Monetary fields represented in integer minor units (paise/cents) or deterministic Decimal types (no floating point).
3. Foreign key relationships and audit timestamp fields established.
4. Migration framework configured and initial migration generated.
5. Automated tests verifying database session lifecycle and model creation.

## 20. Last Verified State

* **Date:** 2026-08-31
* **Backend Automated Tests:** `tests/test_health.py::test_health_check_returns_200` PASSED (100%).
* **Backend Server Startup:** Uvicorn started on `http://127.0.0.1:8000`, `GET /health` returned HTTP 200 `{"status": "ok"}`.
* **Frontend Type Checking:** `tsc --noEmit` passed with 0 errors.
* **Frontend Production Build:** `next build` completed successfully.
* **Frontend Server Startup:** Next.js started on `http://localhost:3000`, `GET /` returned HTTP 200.
* **Security Check:** Verified no `.env` files or secrets committed, no hardcoded API keys.
* **Phase Leakage Check:** Verified no LLM, Razorpay, auth, or business logic code introduced.

## 21. Next Phase

* **Next Phase:** Phase 1 — Database & Data Model
* **Status:** IN PROGRESS (Specification and implementation pending execution approval)
