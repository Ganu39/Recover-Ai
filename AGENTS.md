# ENGINEERING RULES & SYSTEM CONSTRAINTS

## Phase discipline

Only implement the current phase.

Never implement future phases unless explicitly instructed.

After completing the requested phase, stop.

Do not automatically continue to another phase.

## Anti-hallucination

Never invent:

* APIs
* API endpoints
* request fields
* response fields
* database fields
* external service capabilities
* test results

If information is unknown, explicitly say it is unknown.

For Razorpay functionality, official Razorpay documentation is the source of truth.

Never claim a Razorpay integration works unless it has actually been tested.

## Financial safety

Never allow an LLM to directly perform unrestricted financial actions.

Financial calculations must be deterministic.

Do not use floating point for monetary calculations.

Never hardcode credentials.

Use Razorpay Test Mode only during development.

## AI boundaries

The AI/LLM may eventually:

* classify
* diagnose
* explain
* recommend
* summarize

The AI must not independently bypass deterministic safety controls.

## Code quality

Prefer:

* small functions
* explicit interfaces
* typed structures
* automated tests
* clear error handling
* simple architecture

Avoid:

* unnecessary microservices
* unnecessary dependencies
* giant files
* duplicated logic
* premature optimization

## Change discipline

Only modify files required by the current phase.

If you discover a useful future feature, record it instead of implementing it.

---

# SECURITY RULES

* Never commit .env files containing secrets.
* Create .env.example instead.
* Never expose API keys to the frontend.
* Never hardcode credentials.
* Validate external inputs.
* Do not introduce authentication in Phase 0.
* Do not introduce payment execution in Phase 0.
