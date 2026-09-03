# RecoverAI

RecoverAI is an AI-powered Revenue Recovery platform designed to detect at-risk revenue from failed payments, checkout abandonment, and subscription payment failures, diagnose root causes, estimate recovery probabilities, recommend recovery interventions, and execute permitted recovery actions deterministically through payment gateways while strictly maintaining safety policies, financial controls, and complete auditability.

## System Status

**Phases 0–7 COMPLETE | Production-Quality Operations Frontend COMPLETE**

RecoverAI provides an end-to-end fintech revenue-recovery command center for the **Razorpay AI Buildathon** (AI Revenue Recovery Track).

```text
Revenue at Risk → Risk Detection → AI Root-Cause Diagnosis → Recovery Decision → Safety Gateway → Bounded Execution → Confirmed Recovered Revenue
```

### Key Metrics (Seed 42 Benchmark)
* **Total Exposure Evaluated:** ₹53,11,619.66 (1,676 failed payments)
* **Gateway Authorized Recoverable:** ₹8,52,597.35 (689 cases)
* **Confirmed Reconciled Recovery:** ₹5,61,955.98 (456 executions, 65.9% yield)
* **Deferred Cooldown:** ₹2,90,641.37 (233 cases)
* **Safety Invariant Violations:** **0 bps (Zero violations)**
* **Automated Regression Suite:** **201 passing tests** across all phases

## Razorpay Test Mode Integration

RecoverAI connects directly with **Razorpay Test Mode** using official supported APIs:

* **Chosen Gateway Operation:** Official **Razorpay Orders API** (`POST /v1/orders` / `client.order.create`). Razorpay does not support direct failed payment retries (`POST /payments/:id/retry`); recovering revenue is executed by issuing an authoritative Order for the exact integer paise amount and INR currency.
* **Payment Lifecycle Semantics:** Order creation creates a gateway order (`ORDER_CREATED` / `AWAITING_PAYMENT`, Recovered: ₹0.00). Revenue is only confirmed when an authoritative payment event is verified.
* **Webhook Signature Verification:** `POST /api/v1/webhooks/razorpay` processes `order.paid`, `payment.captured`, `payment_link.paid`, and `payment.failed` with constant-time HMAC-SHA256 signature verification (`X-Razorpay-Signature`).
* **Deduplication & Replay Safety:** `X-Razorpay-Event-Id` prevents duplicate event processing and prevents double-counting revenue.
* **Security & Credential Boundaries:** Enforces `rzp_test_...` key prefix. Live credentials (`rzp_live_...`) and non-test environments fail closed immediately with a `SecurityError`. Zero secrets in logs, audit records, or frontend client.
* **Controlled End-to-End Demo:** `POST /api/v1/demo/razorpay-recovery` runs a full 7-stage live trace with verified reconciliation.

## Technology Stack

* **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Lucide Icons, Stitch MCP Design System
* **Backend:** Python 3.14+, FastAPI, Uvicorn, Pydantic, Alembic
* **Payment Integration:** Razorpay Test Mode (`razorpay` SDK + HTTP Basic Auth + HMAC-SHA256 Webhook Verification)
* **Database:** PostgreSQL (SQLAlchemy 2.0+, asyncpg 0.31+)
* **Synthetic Engine:** Deterministic RNG, integer basis points, evaluation metadata layer
* **Risk Engine:** Deterministic rule-based baseline (`v1`), air-gapped evaluation harness
* **AI Diagnosis Engine:** Read-only analytical reasoner (`v1`), provider abstraction (`MockLLMProvider`, `GenericHTTPLLMProvider`), structured evidence grounding
* **Recovery Decision Agent:** Policy-first recommendation engine (`v1`/`v1`), deterministic proposal UUIDs (`uuid5`), strict safety hard blocks
* **Deterministic Safety Gateway:** Phase 6 multi-stage invariant validation, kill switch, sliding-window rate limiting, replay protection
* **Bounded Recovery Execution:** Phase 7 test-mode provider dispatch (`RazorpayTestProvider`, `MockPaymentProvider`), webhook reconciliation, atomic idempotency

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
2. Configure your Razorpay Test Mode credentials in `.env`:
   ```env
   RAZORPAY_KEY_ID=rzp_test_your_key_id
   RAZORPAY_KEY_SECRET=your_test_key_secret
   RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
   RAZORPAY_ENV=test
   ```

### Running the Services
1. **Start Backend API:**
   ```bash
   .\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend Web App:**
   ```bash
   cd apps/web && npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to view the Operations Command Center.

### Running Automated Tests
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_razorpay_integration.py tests/test_execution_layer.py -v
```

