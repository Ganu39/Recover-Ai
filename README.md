# RecoverAI

RecoverAI is an AI-powered Revenue Recovery platform designed to detect at-risk revenue from failed payments, checkout abandonment, and subscription payment failures, diagnose root causes, estimate recovery probabilities, recommend recovery interventions, and execute permitted recovery actions deterministically through payment gateways while strictly maintaining safety policies, financial controls, and complete auditability.

## Current Development Phase

**Phase 1 — Database & Data Model**

> **Note on Razorpay Integration:** Razorpay Test Mode integration is strictly deferred to a later phase (Phase 7). No live or test Razorpay credentials or payment processing logic are implemented during Phase 1.

## Technology Stack

* **Frontend:** Next.js (React), TypeScript, Tailwind CSS
* **Backend:** Python 3.14+, FastAPI, Uvicorn, Pydantic, Alembic
* **Database:** PostgreSQL (SQLAlchemy 2.0+, asyncpg 0.31+)
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
│   └── migrations/        # Alembic database migration scripts
├── agents/                # AI Agent definitions (deferred to future phases)
├── services/              # Domain services (deferred to future phases)
├── tests/                 # Automated test suite (health check & PostgreSQL database tests)
├── docs/                  # System architecture, data model, and phase specifications
│   ├── data-model.md      # Data model ERD, schema, constraints, and status taxonomies
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

To roll back migrations:
```bash
alembic downgrade base
```

Detailed database architecture and schema details are documented in [docs/data-model.md](docs/data-model.md).

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

Run all automated tests (health check and PostgreSQL database tests):
```bash
pytest tests/ -v
```

Run frontend type checking / build:
```bash
cd apps/web
npm run build
```
