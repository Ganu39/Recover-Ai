# Phase 0 — Foundation and Engineering Rules

## 1. Objective
Establish a clean repository structure, foundational FastAPI backend, minimal Next.js frontend, database connection abstraction, automated testing foundation, engineering constraints, and persistent context management.

## 2. Scope
* Root directory structure: `apps/web/`, `apps/api/`, `agents/`, `services/`, `data/`, `tests/`, `docs/`.
* Next.js TypeScript Tailwind frontend placeholder.
* FastAPI backend with `GET /health` returning `{"status": "ok"}`.
* PostgreSQL async connection abstraction.
* Safe `.env.example` template without secrets.
* `AGENTS.md` and `README.md`.
* Automated test for `/health`.

## 3. Allowed Changes
* Creating initial directory layout.
* Baseline configuration and dependency manifests.
* Minimal health endpoint and testing harness.

## 4. Forbidden Changes
* No AI/LLM integration.
* No Razorpay API keys or integration logic.
* No authentication.
* No business tables, transaction models, or recovery logic.

## 5. Acceptance Criteria
1. FastAPI starts and `GET /health` returns `{"status": "ok"}` (HTTP 200).
2. Next.js starts and renders placeholder without runtime/type errors.
3. Automated pytest suite runs and passes.
4. `.env.example` and `AGENTS.md` present.
5. No secrets or future-phase functionality introduced.

## 6. Completion Status
**COMPLETE** (Verified on 2026-08-31).
