# Phase 1 — Database & Data Model

## 1. Objective
Create the foundational PostgreSQL data model and migration framework for RecoverAI.
Establish relational structures for customers, payments, payment attempts, subscriptions, and recovery opportunities with strict database-level constraints and integer minor units for monetary safety.

## 2. Scope & Exact Entities
Create exactly these five entities:
1. **Customer**:
   - `id` (UUID / Integer PK)
   - `external_customer_id` (String, Unique, Indexed)
   - `email` (String, Indexed)
   - `name` (String, Nullable)
   - `created_at`, `updated_at` (DateTime with timezone)
2. **Payment**:
   - `id` (UUID / Integer PK)
   - `external_payment_id` (String, Unique, Indexed)
   - `customer_id` (FK to Customer.id, Indexed)
   - `amount_minor` (BigInteger / Integer, non-negative CHECK)
   - `currency` (String, length 3)
   - `status` (Enum: `created`, `authorized`, `captured`, `failed`, `refunded`, etc.)
   - `created_at`, `updated_at` (DateTime with timezone)
3. **PaymentAttempt**:
   - `id` (UUID / Integer PK)
   - `payment_id` (FK to Payment.id, Indexed)
   - `attempt_number` (Integer, > 0 CHECK)
   - `status` (Enum: `initiated`, `successful`, `failed`)
   - `failure_code` (String, Nullable)
   - `failure_reason` (String, Nullable)
   - `attempted_at` (DateTime with timezone, Indexed)
4. **Subscription**:
   - `id` (UUID / Integer PK)
   - `external_subscription_id` (String, Unique, Indexed)
   - `customer_id` (FK to Customer.id, Indexed)
   - `amount_minor` (BigInteger / Integer, non-negative CHECK)
   - `currency` (String, length 3)
   - `status` (Enum: `active`, `past_due`, `cancelled`, `halted`, etc.)
   - `interval` (String: `monthly`, `yearly`, `weekly`, etc.)
   - `created_at`, `updated_at` (DateTime with timezone)
5. **RecoveryCase**:
   - `id` (UUID / Integer PK)
   - `payment_id` (FK to Payment.id, Nullable, Indexed)
   - `subscription_id` (FK to Subscription.id, Nullable, Indexed)
   - `status` (Enum: `detected`, `evaluating`, `action_pending`, `recovered`, `unrecoverable`, `closed`)
   - `amount_at_risk_minor` (BigInteger / Integer, non-negative CHECK)
   - `currency` (String, length 3)
   - `detected_at` (DateTime with timezone, Indexed)
   - `resolved_at` (DateTime with timezone, Nullable)
   - **Constraint**: Must reference either `payment_id` OR `subscription_id` (not neither: `CHECK (payment_id IS NOT NULL OR subscription_id IS NOT NULL)`).

## 3. Allowed Changes
* Creating SQLAlchemy ORM models in `data/models/` or `apps/api/models/`.
* Setting up Alembic in `data/migrations/` (or `alembic/`) with initial migration.
* Database constraint definitions (CHECK constraints, foreign keys, unique constraints, indexes).
* Automated database tests under `tests/test_database.py` testing entity lifecycles, constraints, and relationships.
* Creating `docs/data-model.md`.
* Updating `README.md` and `docs/PROJECT_CONTEXT.md`.

## 4. Forbidden Changes
* No AI/LLM integration or prompt engineering.
* No Razorpay API SDK, endpoints, or webhooks.
* No payment execution or retry mechanics.
* No recovery probability or AI scoring fields.
* No agent decision, audit log, or analytics tables (deferred to future phases).
* No business API endpoints or frontend database connections.
* No floating-point types for monetary values.

## 5. Acceptance Criteria
1. All 5 entities implemented with typed SQLAlchemy models and database-level constraints.
2. Monetary values strictly use integer minor units (BigInteger / Integer).
3. Relationships (1-to-many Customer->Payment, Payment->PaymentAttempt, Customer->Subscription, Payment/Subscription->RecoveryCase) work as expected.
4. Validation and constraint rejection tests pass (negative money, invalid attempt numbers, duplicate unique external IDs, missing references in RecoveryCase, invalid status values).
5. Alembic migration script exists and reproduces the schema.
6. Backend `/health` regression test passes.
7. `docs/data-model.md` created with complete documentation.
8. `docs/PROJECT_CONTEXT.md` updated with accurate verified state.

## 6. Completion Status
**COMPLETE** (Verified on 2026-08-31 against native PostgreSQL 16).
