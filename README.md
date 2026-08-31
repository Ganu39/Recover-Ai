# RecoverAI

RecoverAI is an AI-powered Revenue Recovery platform designed to detect at-risk revenue from failed payments, checkout abandonment, and subscription payment failures, diagnose root causes, estimate recovery probabilities, recommend recovery interventions, and execute permitted recovery actions deterministically through payment gateways while strictly maintaining safety policies, financial controls, and complete auditability.

## Current Development Phase

**Phase 4 — AI Root-Cause Diagnosis**

> **Note on Razorpay Integration:** Razorpay Test Mode integration is strictly deferred to a later phase (Phase 7). No live or test Razorpay credentials or payment processing logic are implemented during Phase 4.

## Technology Stack

* **Frontend:** Next.js (React), TypeScript, Tailwind CSS
* **Backend:** Python 3.14+, FastAPI, Uvicorn, Pydantic, Alembic
* **Database:** PostgreSQL (SQLAlchemy 2.0+, asyncpg 0.31+)
* **Synthetic Engine:** Deterministic RNG, integer basis points, evaluation metadata layer
* **Risk Engine:** Deterministic rule-based baseline (`v1`), air-gapped evaluation harness, basis-point metrics
* **AI Diagnosis Engine:** Read-only analytical reasoner (`v1`), provider abstraction (`MockLLMProvider`, `GenericHTTPLLMProvider`), evidence grounding, Pydantic schema validation
* **Testing:** Pytest, HTTPX, pytest-asyncio

## Repository Structure

```text
recover-ai/
├── apps/
│   ├── web/               # Next.js frontend application
│   └── api/               # FastAPI backend application
│       ├── core/          # Configuration and database connection abstraction
│       └── main.py        # FastAPI entrypoint with /health endpoint
├── data/
│   ├── models/            # Canonical database models (Customer, Payment, etc.)
│   ├── migrations/        # Alembic database migration scripts
│   └── synthetic/         # Deterministic synthetic data generator & seeder
├── agents/
│   └── diagnosis/         # Read-only AI Root-Cause Diagnosis Agent (Phase 4)
│       ├── prompts/       # Immutable versioned prompt templates (v1)
│       ├── providers/     # Base, Mock, and HTTP LLM providers
│       ├── context_builder.py # Sanitized context extractor
│       ├── evaluator.py   # AI diagnosis evaluation harness
│       ├── schemas.py     # Pydantic schemas & taxonomy definitions
│       └── service.py     # DiagnosisAgent orchestration
├── services/
│   └── risk_engine/       # Deterministic Revenue-Risk Engine (Baseline v1)
├── tests/                 # Automated test suite (health, DB, synthetic, risk engine, AI diagnosis)
├── docs/                  # System architecture, data model, scenarios, and phase specifications
│   ├── data-model.md      # Data model ERD, schema, constraints, and status taxonomies
│   ├── synthetic-scenarios.md # Canonical 8 recovery scenario archetypes & ground truth
│   ├── synthetic-data.md  # Synthetic data generator architecture & statistics
│   ├── risk-engine.md     # Baseline v1 rules, reason codes, metrics & benchmark results
│   ├── ai-diagnosis.md    # AI diagnosis architecture, taxonomy, prompts & evaluation
│   ├── benchmark_v1.json  # Frozen benchmark report for Baseline v1 (Seed 42)
│   ├── benchmark_ai_mock.json # Mock infrastructure validation scorecard
│   ├── PROJECT_CONTEXT.md # Canonical persistent project context
│   └── PHASES/            # Phase specification files
├── .env.example           # Environment template
├── .gitignore             # Root git ignore rules
├── AGENTS.md              # Engineering rules and safety constraints
├── alembic.ini            # Alembic migration configuration
└── README.md              # Project overview and setup instructions
```

## Local Setup Instructions

### Prerequisites
* Python 3.10+ (tested on Python 3.14)
* Node.js v18+ (tested on Node.js v24)
* PostgreSQL 16+
* npm

### Environment Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set your PostgreSQL `DATABASE_URL` in `.env`.

### Backend Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
2. Install backend dependencies:
   ```bash
   pip install -r apps/api/requirements.txt
   ```

### Database Migrations
Apply Alembic migrations to create the database schema:
```bash
alembic upgrade head
```

### Synthetic Data Generation & Seeding
Generate 1,000 customers and 5,000 payments with summary statistics:
```bash
python -m data.synthetic.cli --seed 42 --customers 1000 --payments 5000
```

Seed the generated dataset into PostgreSQL:
```bash
python -m data.synthetic.cli --seed 42 --customers 1000 --payments 5000 --seed-db
```

### Risk Engine Baseline Benchmark (v1)
Run the deterministic revenue-risk evaluation benchmark:
```bash
python -m services.risk_engine.cli --seed 42 --customers 1000 --payments 5000 --output docs/benchmark_v1.json
```

### AI Root-Cause Diagnosis Benchmark
Run the AI root-cause diagnosis benchmark (using mock provider for local validation):
```bash
python -m agents.diagnosis.cli --seed 42 --customers 1000 --payments 5000 --output docs/benchmark_ai_mock.json
```

Detailed documentation:
* [docs/risk-engine.md](docs/risk-engine.md) — Baseline v1 specification & benchmark
* [docs/ai-diagnosis.md](docs/ai-diagnosis.md) — AI diagnosis taxonomy, prompts & evaluation harness

### Frontend Setup
1. Navigate to the frontend workspace and install dependencies:
   ```bash
   cd apps/web
   npm install
   cd ../..
   ```

## Starting Services

### Starting the Backend
From the repository root:
```bash
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify the health endpoint:
```bash
curl http://127.0.0.1:8000/health
# Response: {"status": "ok"}
```

### Starting the Frontend
From `apps/web`:
```bash
cd apps/web
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

## Running Tests

Run all automated tests (health check, PostgreSQL database tests, synthetic engine tests):
```bash
pytest tests/ -v
```

Run frontend type checking / build:
```bash
cd apps/web
npm run build
```
