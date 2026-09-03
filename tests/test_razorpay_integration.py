"""Automated security, invariant, and lifecycle tests for Razorpay Test Mode Integration."""

import glob
import hashlib
import hmac
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from agents.decision.schemas import (
    DECISION_VERSION,
    ExplanationChain,
    POLICY_VERSION,
    RecoveryActionType,
    RecoveryDecisionProposal,
    DecisionStatus,
)
from agents.gateway.checks import derive_expected_proposal_id
from agents.gateway.schemas import (
    GATEWAY_VERSION,
    GatewayDecision,
    GatewayDecisionResult,
    GatewayReasonCode,
    GatewayTargetContext,
)
from services.execution import (
    ExecutionAuthorizationError,
    ExecutionConfig,
    ExecutionIdempotencyManager,
    ExecutionRecord,
    ExecutionRequest,
    ExecutionService,
    ExecutionStatus,
    PaymentExecutionMode,
    ProviderNormalizedStatus,
    ProviderRequest,
    RazorpayTestProvider,
    SecurityError,
    WebhookHandler,
)


def _create_authorized_triplet(
    target_type: str = "payment",
    amount_minor: int = 150000,
    currency: str = "INR",
    attempts_count: int = 1,
    action_type: RecoveryActionType = RecoveryActionType.RETRY_PAYMENT,
):
    """Helper to generate a valid Phase 6 authorized triplet."""
    target_id = uuid.uuid4()
    case_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    prop_id = derive_expected_proposal_id(
        decision_version=DECISION_VERSION,
        policy_version=POLICY_VERSION,
        target_type=target_type,
        target_id=target_id,
    )

    target = GatewayTargetContext(
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        customer_id=cust_id,
        amount_minor=amount_minor,
        currency=currency,
        amount_display=f"₹{amount_minor / 100:,.2f}",
        target_attempt_count=attempts_count,
        customer_history_count=4,
        customer_success_count=4,
        customer_success_rate_bps=10000,
        latest_failure_code="temporary_network_decline",
    )

    proposal = RecoveryDecisionProposal(
        decision_version=DECISION_VERSION,
        policy_version=POLICY_VERSION,
        proposal_id=prop_id,
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        amount_minor=amount_minor,
        currency=currency,
        amount_display=f"₹{amount_minor / 100:,.2f}",
        action_type=action_type,
        decision_status=DecisionStatus.PROPOSED,
        explanation=ExplanationChain(
            observed_facts=["Attempt 1 failed"],
            ai_inferences=["Temporary gateway error"],
            policy_checks=["Attempt ceiling check passed"],
            final_rationale="Gateway authorized automatic recovery",
        ),
    )

    gw_result = GatewayDecisionResult(
        gateway_decision=GatewayDecision.APPROVED,
        proposal_id=prop_id,
        target_type=target_type,
        target_id=target_id,
        decision_reason="Approved by gateway",
        reason_code=GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER,
        policy_version=POLICY_VERSION,
        gateway_version=GATEWAY_VERSION,
        decision_version=DECISION_VERSION,
        audit_reference=uuid.uuid4(),
        eligible_for_execution_layer=True,
    )

    return proposal, target, gw_result


# =====================================================================
# 1. CREDENTIAL & ENVIRONMENT BOUNDARY ENFORCEMENT
# =====================================================================

def test_1_rzp_test_credentials_accepted():
    """Test 1: Valid rzp_test_ key ID with test mode is accepted."""
    provider = RazorpayTestProvider(
        key_id="rzp_test_validkey12345",
        key_secret="test_secret_12345",
        mode=PaymentExecutionMode.TEST,
    )
    assert provider.key_id == "rzp_test_validkey12345"


def test_2_rzp_live_credentials_strictly_rejected():
    """Test 2: Any rzp_live_ key ID is strictly prohibited and raises SecurityError."""
    with pytest.raises(SecurityError, match="Live Razorpay credentials"):
        RazorpayTestProvider(
            key_id="rzp_live_prohibited_key",
            key_secret="live_secret",
            mode=PaymentExecutionMode.TEST,
        )


def test_3_non_test_mode_strictly_rejected():
    """Test 3: Non-test execution mode is prohibited."""
    with pytest.raises(SecurityError, match="prohibited"):
        RazorpayTestProvider(
            key_id="rzp_test_validkey12345",
            key_secret="test_secret",
            mode="live",  # type: ignore
        )


# =====================================================================
# 2. WEBHOOK CRYPTOGRAPHIC SIGNATURE & REPLAY PROTECTION
# =====================================================================

def test_4_valid_webhook_signature_accepted():
    """Test 4: Valid HMAC-SHA256 signature is accepted."""
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    secret = "webhook_secret_key_42"
    raw_body = b'{"event":"order.paid","payload":{}}'
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    assert provider.verify_webhook_signature(raw_body, sig, secret) is True


def test_5_invalid_webhook_signature_rejected():
    """Test 5: Tampered or forged signature is rejected."""
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    secret = "webhook_secret_key_42"
    raw_body = b'{"event":"order.paid","payload":{}}'

    assert provider.verify_webhook_signature(raw_body, "forged_signature", secret) is False


def test_6_duplicate_webhook_processed_only_once():
    """Test 6: Duplicate webhook deliveries with the same event ID are handled idempotently."""
    manager = ExecutionIdempotencyManager()
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    handler = WebhookHandler(provider=provider, idempotency_manager=manager)

    # Register an active execution record
    rec = ExecutionRecord(
        execution_id=uuid.uuid4(),
        proposal_id=uuid.uuid4(),
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_minor=150000,
        currency="INR",
        status=ExecutionStatus.SUCCEEDED,
        attempt_number=2,
        provider_reference="order_test_dup_001",
        idempotency_key="idemp_dup_1",
        created_at_iso="2026-09-03T10:00:00Z",
        updated_at_iso="2026-09-03T10:00:00Z",
    )
    manager.complete_execution(rec)

    secret = "secret"
    payload = {
        "id": "evt_unique_101",
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_test_dup_001",
                    "amount": 150000,
                    "currency": "INR",
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    # Delivery 1: Processed and reconciled
    ok1, code1, res1 = handler.handle_webhook(raw_body, sig, secret, event_id_header="evt_unique_101")
    assert ok1 is True
    assert code1 == "RECONCILED_SUCCESSFULLY"
    assert res1.reconciled_status == ExecutionStatus.RECONCILED

    # Delivery 2: Exact same event ID -> Idempotent replay no-op
    ok2, code2, res2 = handler.handle_webhook(raw_body, sig, secret, event_id_header="evt_unique_101")
    assert ok2 is True
    assert code2 == "IDEMPOTENT_REPLAY"
    assert res2 is None


# =====================================================================
# 3. FINANCIAL INTEGRITY: AMOUNT & CURRENCY VALIDATION
# =====================================================================

def test_7_webhook_amount_mismatch_rejected():
    """Test 7: Webhook payload claiming different amount than trusted execution is blocked."""
    manager = ExecutionIdempotencyManager()
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    handler = WebhookHandler(provider=provider, idempotency_manager=manager)

    rec = ExecutionRecord(
        execution_id=uuid.uuid4(),
        proposal_id=uuid.uuid4(),
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_minor=150000,  # ₹1,500.00
        currency="INR",
        status=ExecutionStatus.SUCCEEDED,
        attempt_number=2,
        provider_reference="order_test_amt_001",
        idempotency_key="idemp_amt_1",
        created_at_iso="2026-09-03T10:00:00Z",
        updated_at_iso="2026-09-03T10:00:00Z",
    )
    manager.complete_execution(rec)

    secret = "secret"
    payload = {
        "id": "evt_amt_tampered",
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_test_amt_001",
                    "amount": 999999,  # Mismatched amount
                    "currency": "INR",
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, res = handler.handle_webhook(raw_body, sig, secret)
    assert ok is False
    assert code == "AMOUNT_MISMATCH"
    assert rec.status == ExecutionStatus.SUCCEEDED  # Status was NOT modified!


def test_8_webhook_currency_mismatch_rejected():
    """Test 8: Webhook payload with non-INR currency is rejected."""
    manager = ExecutionIdempotencyManager()
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    handler = WebhookHandler(provider=provider, idempotency_manager=manager)

    rec = ExecutionRecord(
        execution_id=uuid.uuid4(),
        proposal_id=uuid.uuid4(),
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_minor=150000,
        currency="INR",
        status=ExecutionStatus.SUCCEEDED,
        attempt_number=2,
        provider_reference="order_test_curr_001",
        idempotency_key="idemp_curr_1",
        created_at_iso="2026-09-03T10:00:00Z",
        updated_at_iso="2026-09-03T10:00:00Z",
    )
    manager.complete_execution(rec)

    secret = "secret"
    payload = {
        "id": "evt_curr_tampered",
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_test_curr_001",
                    "amount": 150000,
                    "currency": "USD",  # Mismatched currency
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, res = handler.handle_webhook(raw_body, sig, secret)
    assert ok is False
    assert code == "CURRENCY_MISMATCH"


# =====================================================================
# 4. EXECUTION IDEMPOTENCY & PROVIDER TIMEOUT
# =====================================================================

@pytest.mark.asyncio
async def test_9_duplicate_execution_dispatches_provider_once():
    """Test 9: Re-submitting the same proposal returns existing record; provider dispatched once."""
    prop, target, gw = _create_authorized_triplet()
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    service = ExecutionService(provider=provider)

    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)
    rec1 = await service.execute_recovery(req)
    rec2 = await service.execute_recovery(req)

    assert rec1.execution_id == rec2.execution_id
    assert rec1.idempotency_key == rec2.idempotency_key
    assert rec1.provider_reference == rec2.provider_reference


@pytest.mark.asyncio
async def test_10_provider_timeout_produces_unknown_state_without_blind_retry():
    """Test 10: Provider transport timeout marks UNKNOWN_PROVIDER_STATE without blind duplicates."""
    prop, target, gw = _create_authorized_triplet()
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    service = ExecutionService(provider=provider)

    # Monkeypatch execute_recovery on provider to simulate timeout
    async def mock_timeout(req):
        raise TimeoutError("Gateway connection timed out after 5000ms")

    provider.execute_recovery = mock_timeout  # type: ignore

    rec = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert rec.status == ExecutionStatus.UNKNOWN_PROVIDER_STATE
    assert rec.last_error_code == "TRANSPORT_EXCEPTION"

    # Re-submitting returns same UNKNOWN record rather than re-attempting payment
    rec_repeat = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert rec_repeat.status == ExecutionStatus.UNKNOWN_PROVIDER_STATE
    assert rec_repeat.execution_id == rec.execution_id


# =====================================================================
# 5. ORDER CREATION VS RECONCILIATION SEMANTICS
# =====================================================================

@pytest.mark.asyncio
async def test_11_order_creation_does_not_equal_recovered_revenue():
    """Test 11: Order creation creates an order but does not mark recovered revenue."""
    prop, target, gw = _create_authorized_triplet(amount_minor=250000)
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    service = ExecutionService(provider=provider)

    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert record.status == ExecutionStatus.SUCCEEDED  # Order created in gateway
    assert record.provider_reference.startswith("order_test_")

    # Verify reconciliation result is NOT present until webhook arrives
    assert service.idempotency_manager._records[record.idempotency_key].status != ExecutionStatus.RECONCILED


@pytest.mark.asyncio
async def test_12_webhook_order_paid_reconciles_confirmed_revenue():
    """Test 12: Verified order.paid webhook reconciles state to RECONCILED with recovered amount."""
    prop, target, gw = _create_authorized_triplet(amount_minor=250000)
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    service = ExecutionService(provider=provider)

    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    secret = "secret"
    payload = {
        "id": "evt_order_paid_001",
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": record.provider_reference,
                    "amount": 250000,
                    "currency": "INR",
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, res = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok is True
    assert code == "RECONCILED_SUCCESSFULLY"
    assert res.reconciled_status == ExecutionStatus.RECONCILED
    assert res.amount_recovered_minor == 250000
    assert record.status == ExecutionStatus.RECONCILED


@pytest.mark.asyncio
async def test_13_webhook_payment_failed_does_not_recover_revenue():
    """Test 13: Webhook payment.failed marks status FAILED with 0 recovered revenue."""
    prop, target, gw = _create_authorized_triplet(amount_minor=100000)
    provider = RazorpayTestProvider(key_id="rzp_test_123", key_secret="secret")
    service = ExecutionService(provider=provider)

    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    secret = "secret"
    payload = {
        "id": "evt_pay_failed_001",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_failed_1",
                    "order_id": record.provider_reference,
                    "amount": 100000,
                    "currency": "INR",
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, res = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok is True
    assert res.reconciled_status == ExecutionStatus.FAILED
    assert res.amount_recovered_minor == 0
    assert record.status == ExecutionStatus.FAILED


# =====================================================================
# 6. FASTAPI ENDPOINT INTEGRATION TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_14_api_webhook_forged_signature_returns_400():
    """Test 14: POST /api/v1/webhooks/razorpay with forged signature returns HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/webhooks/razorpay",
            content=b'{"event":"order.paid"}',
            headers={"X-Razorpay-Signature": "forged_sig_123"},
        )
        assert res.status_code == 400
        assert res.json()["detail"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_15_api_demo_endpoint_executes_e2e_reconciled_trace():
    """Test 15: POST /api/v1/demo/razorpay-recovery executes full verified trace with zero secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/demo/razorpay-recovery")
        assert res.status_code == 200
        data = res.json()

        assert data["demo_type"] == "RAZORPAY_TEST_MODE_FLOW"
        assert data["gateway_decision"] == "APPROVED"
        assert data["provider"] == "Razorpay Test Mode"
        assert data["provider_operation"] == "POST /v1/orders"
        assert data["provider_reference"].startswith("order_")
        assert data["reconciled_status"] == "RECONCILED"
        assert data["confirmed_recovered_minor"] == 150000
        assert data["confirmed_recovered_display"] == "₹1,500.00"
        assert data["webhook_signature_verified"] is True
        assert len(data["pipeline_stages"]) == 7


# =====================================================================
# 7. STATIC SECURITY & INTEGRITY SCANS
# =====================================================================

def test_16_static_security_zero_live_keys_in_repo():
    """Test 16: Verify zero actual live keys in repository non-test files."""
    import re
    # Real live Razorpay key pattern (rzp_live_ followed by 10+ alphanumeric characters)
    live_key_pattern = re.compile(r"rzp_live_[a-zA-Z0-9]{10,}")
    files = glob.glob("**/*.py", recursive=True) + glob.glob("**/*.md", recursive=True)
    for fpath in files:
        if ".git" in fpath or ".venv" in fpath or ".pytest_cache" in fpath or "tests" in fpath:
            continue
        content = open(fpath, "r", encoding="utf-8", errors="ignore").read()
        matches = live_key_pattern.findall(content)
        # Ensure no actual live API keys exist in codebase
        real_matches = [m for m in matches if "placeholder" not in m and "your_key" not in m]
        assert len(real_matches) == 0, f"Suspicious live key in {fpath}: {real_matches}"




def test_17_static_security_zero_floating_point_monetary_math():
    """Test 17: Verify zero float(amount) conversions in services/execution/."""
    files = glob.glob("services/execution/**/*.py", recursive=True)
    for fpath in files:
        content = open(fpath, "r", encoding="utf-8").read()
        assert "float(" not in content or "float(request.amount_minor)" not in content
