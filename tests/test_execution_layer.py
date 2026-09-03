"""Automated security, invariant, and lifecycle tests for Phase 7 Execution Layer."""

import ast
import glob
import json
import uuid
import pytest

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
    BasePaymentProvider,
    ExecutionAuthorizationError,
    ExecutionConfig,
    ExecutionEvaluator,
    ExecutionIdempotencyManager,
    ExecutionRecord,
    ExecutionRequest,
    ExecutionService,
    ExecutionStateMachine,
    InvalidStateTransitionError,
    MockPaymentProvider,
    PaymentExecutionMode,
    ProviderNormalizedStatus,
    ProviderResponse,
    RazorpayTestProvider,
    SecurityError,
    WebhookHandler,
    derive_execution_idempotency_key,
)
from services.execution.schemas import ExecutionStatus


def _create_authorized_triplet(
    target_type: str = "payment",
    amount_minor: int = 150000,
    currency: str = "INR",
    attempts_count: int = 1,
    action_type: RecoveryActionType = RecoveryActionType.RETRY_PAYMENT,
    gateway_decision: GatewayDecision = GatewayDecision.APPROVED,
    eligible_for_execution: bool = True,
    reason_code: GatewayReasonCode = GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER,
):
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
        latest_failure_code="temporary_failure",
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
            observed_facts=["Observed"],
            ai_inferences=["Inference"],
            policy_checks=["Policy"],
            final_rationale="Rationale",
        ),
    )

    gw_result = GatewayDecisionResult(
        gateway_decision=gateway_decision,
        proposal_id=prop_id,
        target_type=target_type,
        target_id=target_id,
        decision_reason="Approved by gateway",
        reason_code=reason_code,
        policy_version=POLICY_VERSION,
        gateway_version=GATEWAY_VERSION,
        decision_version=DECISION_VERSION,
        audit_reference=uuid.uuid4(),
        eligible_for_execution_layer=eligible_for_execution,
    )

    return proposal, target, gw_result


# =====================================================================
# 1. AUTHORIZATION REVALIDATION & GATEWAY MANDATE
# =====================================================================

@pytest.mark.asyncio
async def test_1_valid_phase_6_approval_executes():
    """Test 1: Proposal with valid Phase 6 APPROVED authorization executes successfully."""
    prop, target, gw = _create_authorized_triplet()
    service = ExecutionService()

    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)
    record = await service.execute_recovery(req)

    assert record.status == ExecutionStatus.SUCCEEDED
    assert record.amount_minor == 150000
    assert record.currency == "INR"
    assert record.provider_reference is not None


@pytest.mark.asyncio
async def test_2_blocked_gateway_decision_cannot_execute():
    """Test 2: Gateway result with BLOCKED decision strictly rejected."""
    prop, target, gw = _create_authorized_triplet(
        gateway_decision=GatewayDecision.BLOCKED,
        eligible_for_execution=False,
        reason_code=GatewayReasonCode.BLOCK_RETRY_LIMIT_EXCEEDED,
    )
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="Gateway decision must be APPROVED"):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_3_requires_review_cannot_execute():
    """Test 3: Gateway result with REQUIRES_REVIEW strictly rejected."""
    prop, target, gw = _create_authorized_triplet(
        gateway_decision=GatewayDecision.REQUIRES_REVIEW,
        eligible_for_execution=False,
        reason_code=GatewayReasonCode.HIGH_VALUE_REQUIRES_REVIEW,
    )
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_4_kill_switch_active_cannot_execute():
    """Test 4: Gateway result with KILL_SWITCH_ACTIVE strictly rejected."""
    prop, target, gw = _create_authorized_triplet(
        gateway_decision=GatewayDecision.KILL_SWITCH_ACTIVE,
        eligible_for_execution=False,
        reason_code=GatewayReasonCode.KILL_SWITCH_ACTIVE,
    )
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_5_eligible_flag_false_cannot_execute():
    """Test 5: eligible_for_execution_layer=False cannot execute even if decision claim is APPROVED."""
    prop, target, gw = _create_authorized_triplet(eligible_for_execution=False)
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="eligible_for_execution_layer is False"):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_6_tampered_proposal_id_rejected():
    """Test 6: Proposal ID mismatch against expected deterministic UUID5 rejected."""
    prop, target, gw = _create_authorized_triplet()
    object.__setattr__(prop, "proposal_id", uuid.uuid4())
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="Proposal identity mismatch"):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_7_tampered_target_id_rejected():
    """Test 7: Target ID mismatch rejected."""
    prop, target, gw = _create_authorized_triplet()
    object.__setattr__(target, "target_id", uuid.uuid4())
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_8_non_executable_action_rejected():
    """Test 8: Non-executable action (NO_ACTION or HUMAN_REVIEW) rejected."""
    prop, target, gw = _create_authorized_triplet(action_type=RecoveryActionType.NO_ACTION)
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="not in executable allowlist"):
        await service.execute_recovery(req)


# =====================================================================
# 2. FINANCIAL INTEGRITY
# =====================================================================

@pytest.mark.asyncio
async def test_9_amount_mismatch_rejected():
    """Test 9: Proposal amount differing from trusted target rejected."""
    prop, target, gw = _create_authorized_triplet(amount_minor=150000)
    object.__setattr__(prop, "amount_minor", 100000)
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="Amount mismatch"):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_10_currency_mismatch_rejected():
    """Test 10: Currency mismatch or non-INR rejected."""
    prop, target, gw = _create_authorized_triplet(currency="INR")
    object.__setattr__(prop, "currency", "USD")
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="Unsupported or mismatched currency"):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_11_provider_receives_exact_authorized_amount():
    """Test 11: Provider adapter receives exact integer paise amount."""
    prop, target, gw = _create_authorized_triplet(amount_minor=275050)
    provider = MockPaymentProvider()
    service = ExecutionService(provider=provider)
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    record = await service.execute_recovery(req)
    assert record.amount_minor == 275050
    # Inspect recorded provider request
    prov_req = provider.recorded_requests[record.idempotency_key]
    assert prov_req.amount_minor == 275050
    assert isinstance(prov_req.amount_minor, int)


# =====================================================================
# 3. RETRY CEILING & ACTION SEMANTICS
# =====================================================================

@pytest.mark.asyncio
async def test_12_attempt_ceiling_enforced():
    """Test 12: Attempts count exceeding configured max ceiling is rejected."""
    prop, target, gw = _create_authorized_triplet(attempts_count=3)
    service = ExecutionService(config=ExecutionConfig(max_execution_attempts=2))
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    with pytest.raises(ExecutionAuthorizationError, match="exceeds ceiling"):
        await service.execute_recovery(req)


@pytest.mark.asyncio
async def test_13_retry_later_sets_deferred():
    """Test 13: RETRY_LATER action transitions to DEFERRED without calling provider."""
    prop, target, gw = _create_authorized_triplet(action_type=RecoveryActionType.RETRY_LATER)
    provider = MockPaymentProvider()
    service = ExecutionService(provider=provider)
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    record = await service.execute_recovery(req)
    assert record.status == ExecutionStatus.DEFERRED
    assert len(provider.recorded_requests) == 0  # Provider not called


# =====================================================================
# 4. IDEMPOTENCY & CONCURRENCY
# =====================================================================

@pytest.mark.asyncio
async def test_14_same_execution_twice_executes_once():
    """Test 14: Submitting the same authorized request twice executes provider exactly once."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider()
    service = ExecutionService(provider=provider)
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    rec1 = await service.execute_recovery(req)
    assert rec1.status == ExecutionStatus.SUCCEEDED
    assert len(provider.recorded_requests) == 1

    # Second submission
    rec2 = await service.execute_recovery(req)
    assert rec2.execution_id == rec1.execution_id
    assert rec2.status == ExecutionStatus.SUCCEEDED
    # Provider was NOT invoked again
    assert len(provider.recorded_requests) == 1


@pytest.mark.asyncio
async def test_15_deterministic_idempotency_key():
    """Test 15: Exact same parameters generate identical idempotency keys."""
    prop, target, gw = _create_authorized_triplet()
    key1 = derive_execution_idempotency_key(prop.proposal_id, "v1", "v1", prop.action_type.value)
    key2 = derive_execution_idempotency_key(prop.proposal_id, "v1", "v1", prop.action_type.value)
    assert key1 == key2
    assert uuid.UUID(key1)


# =====================================================================
# 5. PROVIDER FAILURES & UNKNOWN STATE
# =====================================================================

@pytest.mark.asyncio
async def test_16_provider_decline_marks_failed():
    """Test 16: Provider card decline sets status to FAILED."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider(default_outcome=ProviderNormalizedStatus.DECLINED)
    service = ExecutionService(provider=provider)
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    record = await service.execute_recovery(req)
    assert record.status == ExecutionStatus.FAILED
    assert record.last_error_code == "BAD_REQUEST_PAYMENT_DECLINED"


@pytest.mark.asyncio
async def test_17_provider_timeout_sets_unknown_state():
    """Test 17: Provider transport timeout sets UNKNOWN_PROVIDER_STATE (not FAILED)."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider(default_outcome=ProviderNormalizedStatus.TIMEOUT)
    service = ExecutionService(provider=provider)
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    record = await service.execute_recovery(req)
    assert record.status == ExecutionStatus.UNKNOWN_PROVIDER_STATE
    assert record.last_error_code == "GATEWAY_TIMEOUT"


@pytest.mark.asyncio
async def test_18_reconciliation_after_unknown_state():
    """Test 18: Querying provider reconciles UNKNOWN_PROVIDER_STATE to SUCCESS."""
    provider = MockPaymentProvider()
    ref = "pay_mock_sample_ref"
    provider.recorded_responses[ref] = ProviderResponse(
        provider_reference=ref,
        normalized_status=ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE,
    )

    # Query status
    resp = await provider.query_recovery_status(ref)
    assert resp.normalized_status == ProviderNormalizedStatus.SUCCESS


# =====================================================================
# 6. WEBHOOKS & SIGNATURE VERIFICATION
# =====================================================================

@pytest.mark.asyncio
async def test_19_valid_signed_webhook_reconciles():
    """Test 19: Valid HMAC signed webhook reconciles existing execution to RECONCILED."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider()
    service = ExecutionService(provider=provider)
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    record = await service.execute_recovery(req)
    assert record.status == ExecutionStatus.SUCCEEDED

    secret = "test_webhook_secret_123"
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": record.provider_reference,
                    "amount": record.amount_minor,
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    import hashlib, hmac
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, result = service.webhook_handler.handle_webhook(
        raw_body=raw_body, signature=sig, webhook_secret=secret
    )
    assert ok is True
    assert code == "RECONCILED_SUCCESSFULLY"
    assert result.reconciled_status == ExecutionStatus.RECONCILED
    assert result.amount_recovered_minor == record.amount_minor


@pytest.mark.asyncio
async def test_20_invalid_webhook_signature_rejected():
    """Test 20: Webhook with invalid signature is rejected."""
    service = ExecutionService()
    raw_body = b'{"event":"payment.captured"}'
    ok, code, result = service.webhook_handler.handle_webhook(
        raw_body=raw_body, signature="forged_signature", webhook_secret="secret"
    )
    assert ok is False
    assert code == "INVALID_SIGNATURE"
    assert result is None


@pytest.mark.asyncio
async def test_21_duplicate_webhook_is_idempotent():
    """Test 21: Duplicate webhook delivery is handled idempotently as no-op."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider()
    service = ExecutionService(provider=provider)
    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))

    secret = "secret"
    payload = {
        "id": "event_uuid_1",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": record.provider_reference}}},
    }
    raw_body = json.dumps(payload).encode("utf-8")
    import hashlib, hmac
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    # First delivery
    ok1, code1, _ = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok1 is True
    assert code1 == "RECONCILED_SUCCESSFULLY"

    # Second delivery
    ok2, code2, _ = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok2 is True
    assert code2 == "IDEMPOTENT_REPLAY"


# =====================================================================
# 7. RAZORPAY TEST MODE & LIVE KEY PROTECTION
# =====================================================================

def test_22_live_razorpay_key_strictly_prohibited():
    """Test 22: Passing rzp_live_ key immediately raises SecurityError."""
    with pytest.raises(SecurityError, match="Live Razorpay credentials"):
        RazorpayTestProvider(
            key_id="rzp_live_1234567890abcdef",
            key_secret="live_secret",
            mode=PaymentExecutionMode.TEST,
        )


def test_23_live_payment_mode_strictly_prohibited():
    """Test 23: Passing non-test mode raises SecurityError."""
    with pytest.raises(SecurityError):
        RazorpayTestProvider(
            key_id="rzp_test_1234567890abcdef",
            key_secret="test_secret",
            mode="live",  # type: ignore
        )


def test_24_valid_test_key_accepted():
    """Test 24: rzp_test_ key with test mode accepted."""
    provider = RazorpayTestProvider(
        key_id="rzp_test_1234567890abcdef",
        key_secret="test_secret",
        mode=PaymentExecutionMode.TEST,
    )
    assert provider.key_id == "rzp_test_1234567890abcdef"


# =====================================================================
# 8. STATE MACHINE & AUDIT INTEGRITY
# =====================================================================

def test_25_invalid_state_transition_raises():
    """Test 25: Illegal state transitions raise InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError):
        ExecutionStateMachine.validate_transition(ExecutionStatus.FAILED, ExecutionStatus.SUCCEEDED)

    with pytest.raises(InvalidStateTransitionError):
        ExecutionStateMachine.validate_transition(ExecutionStatus.RECONCILED, ExecutionStatus.EXECUTION_STARTED)


@pytest.mark.asyncio
async def test_26_audit_trail_recorded_without_secrets():
    """Test 26: Complete audit trail recorded and contains zero secrets."""
    prop, target, gw = _create_authorized_triplet()
    service = ExecutionService()
    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))

    events = service.audit_logger.get_events_for_execution(record.execution_id)
    assert len(events) >= 2  # EXECUTION_STARTED, PROVIDER_REQUESTED, PROVIDER_CONFIRMED

    for event in events:
        event_str = str(event.model_dump()).lower()
        assert "rzp_test" not in event_str
        assert "rzp_live" not in event_str
        assert "secret" not in event_str


# =====================================================================
# 9. STATIC SECURITY SCANS
# =====================================================================

def test_27_static_security_zero_razorpay_outside_provider_boundary():
    """Test 27: Verify Razorpay imports exist ONLY inside razorpay_provider.py."""
    py_files = glob.glob("agents/**/*.py", recursive=True) + glob.glob("services/risk_engine/**/*.py", recursive=True)
    for fpath in py_files:
        content = open(fpath, "r", encoding="utf-8").read()
        assert "import razorpay" not in content, f"Forbidden import razorpay in {fpath}"
        assert "from razorpay" not in content, f"Forbidden from razorpay in {fpath}"


def test_28_static_security_zero_floating_point_in_execution():
    """Test 28: Verify zero float(amount) calculations in services/execution/."""
    exec_files = glob.glob("services/execution/**/*.py", recursive=True)
    for fpath in exec_files:
        content = open(fpath, "r", encoding="utf-8").read()
        assert "float(request.amount_minor)" not in content
        assert "float(target.amount_minor)" not in content


# =====================================================================
# 10. EVALUATION & RELEASE METRICS
# =====================================================================

@pytest.mark.asyncio
async def test_29_evaluator_release_metrics_zero_violations():
    """Test 29: ExecutionEvaluator reports 0 unauthorized, 0 duplicate, 0 financial violations."""
    evaluator = ExecutionEvaluator()
    triplets = [_create_authorized_triplet(amount_minor=100000) for _ in range(5)]

    records, report = await evaluator.evaluate_proposals(triplets)
    assert report.authorized_for_execution == 5
    assert report.executions_succeeded == 5
    assert report.unauthorized_execution_rate_bps == 0
    assert report.duplicate_execution_rate_bps == 0
    assert report.financial_integrity_violation_rate_bps == 0
    assert report.recovered_amount_minor == 500000


# =====================================================================
# 11. ADVANCED CONCURRENCY, PERSISTENCE & SECURITY
# =====================================================================

@pytest.mark.asyncio
async def test_30_concurrency_protection():
    """Test 30: Concurrent duplicate requests with same idempotency key are safely protected."""
    import asyncio
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider()
    service = ExecutionService(provider=provider)
    req1 = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)
    req2 = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    results = await asyncio.gather(
        service.execute_recovery(req1),
        service.execute_recovery(req2),
        return_exceptions=True,
    )

    # Exactly one succeeded or both resolved to the same execution record
    successful = [r for r in results if isinstance(r, ExecutionRecord) and r.status == ExecutionStatus.SUCCEEDED]
    assert len(successful) >= 1
    # Provider called at most once
    assert len(provider.recorded_requests) == 1


@pytest.mark.asyncio
async def test_31_process_restart_simulation():
    """Test 31: Simulating service restart with populated idempotency store does not re-execute."""
    prop, target, gw = _create_authorized_triplet()
    manager = ExecutionIdempotencyManager()
    provider = MockPaymentProvider()
    service1 = ExecutionService(provider=provider, idempotency_manager=manager)

    rec1 = await service1.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert len(provider.recorded_requests) == 1

    # Simulate fresh service instance attached to same persistent store
    service2 = ExecutionService(provider=provider, idempotency_manager=manager)
    rec2 = await service2.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))

    assert rec2.execution_id == rec1.execution_id
    assert len(provider.recorded_requests) == 1  # Still 1, zero re-execution


@pytest.mark.asyncio
async def test_32_network_error_sets_unknown_state():
    """Test 32: Network transport error sets UNKNOWN_PROVIDER_STATE."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider(default_outcome=ProviderNormalizedStatus.NETWORK_ERROR)
    service = ExecutionService(provider=provider)

    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert record.status == ExecutionStatus.UNKNOWN_PROVIDER_STATE
    assert record.last_error_code == "CONNECTION_REFUSED"


@pytest.mark.asyncio
async def test_33_webhook_payment_failed_reconciliation():
    """Test 33: Webhook payment.failed reconciles record to FAILED."""
    prop, target, gw = _create_authorized_triplet()
    provider = MockPaymentProvider(default_outcome=ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE)
    service = ExecutionService(provider=provider)

    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert record.status == ExecutionStatus.UNKNOWN_PROVIDER_STATE

    secret = "secret"
    payload = {
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": record.provider_reference}}},
    }
    raw_body = json.dumps(payload).encode("utf-8")
    import hashlib, hmac
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, result = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok is True
    assert code == "RECONCILED_SUCCESSFULLY"
    assert result.reconciled_status == ExecutionStatus.FAILED
    assert result.amount_recovered_minor == 0


def test_34_webhook_malformed_json_rejected():
    """Test 34: Malformed JSON in webhook payload fails closed."""
    service = ExecutionService()
    secret = "secret"
    raw_body = b"not-a-valid-json{"
    import hashlib, hmac
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, result = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok is False
    assert code == "MALFORMED_JSON_PAYLOAD"


def test_35_webhook_missing_provider_reference_rejected():
    """Test 35: Webhook payload without provider reference fails closed."""
    service = ExecutionService()
    secret = "secret"
    raw_body = b'{"event":"payment.captured","payload":{}}'
    import hashlib, hmac
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, result = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok is False
    assert code == "MISSING_PROVIDER_REFERENCE"


def test_36_webhook_unknown_execution_reference_rejected():
    """Test 36: Webhook payload referencing unknown transaction fails closed."""
    service = ExecutionService()
    secret = "secret"
    raw_body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_unknown_12345"}}}}'
    import hashlib, hmac
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    ok, code, result = service.webhook_handler.handle_webhook(raw_body, sig, secret)
    assert ok is False
    assert code == "UNKNOWN_EXECUTION_REFERENCE"


@pytest.mark.asyncio
async def test_37_negative_or_zero_amount_rejected():
    """Test 37: Negative or zero amount fails closed."""
    prop, target, gw = _create_authorized_triplet(amount_minor=0)
    service = ExecutionService()
    with pytest.raises(ExecutionAuthorizationError):
        await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))


@pytest.mark.asyncio
async def test_38_version_mismatch_rejected():
    """Test 38: Version mismatch fails closed."""
    prop, target, gw = _create_authorized_triplet()
    object.__setattr__(prop, "decision_version", "v99")
    service = ExecutionService()
    with pytest.raises(ExecutionAuthorizationError, match="Version contract mismatch"):
        await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))


@pytest.mark.asyncio
async def test_39_subscription_workflow_authorized_executes():
    """Test 39: SUBSCRIPTION_RECOVERY_WORKFLOW action executes successfully."""
    prop, target, gw = _create_authorized_triplet(
        target_type="subscription",
        action_type=RecoveryActionType.SUBSCRIPTION_RECOVERY_WORKFLOW,
    )
    service = ExecutionService()
    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert record.status == ExecutionStatus.SUCCEEDED
    assert record.target_type == "subscription"


@pytest.mark.asyncio
async def test_40_payment_method_update_authorized_executes():
    """Test 40: REQUEST_PAYMENT_METHOD_UPDATE action executes successfully."""
    prop, target, gw = _create_authorized_triplet(
        action_type=RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE,
    )
    service = ExecutionService()
    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert record.status == ExecutionStatus.SUCCEEDED
    assert record.action_type == RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE


def test_41_env_example_contains_placeholders_only():
    """Test 41: .env.example contains only non-secret placeholders."""
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read().lower()
    assert "rzp_live" not in content
    assert "password" not in content or "postgres" in content


def test_42_static_security_zero_ai_invocation_in_execution():
    """Test 42: Execution service modules do not import or call AI diagnosis directly."""
    exec_files = [f for f in glob.glob("services/execution/**/*.py", recursive=True) if not f.endswith("cli.py")]
    for fpath in exec_files:
        content = open(fpath, "r", encoding="utf-8").read()
        assert "from agents.diagnosis" not in content
        assert "import agents.diagnosis" not in content


def test_43_static_security_zero_ground_truth_in_execution():
    """Test 43: Execution modules do not import or use RecoveryGroundTruth."""
    exec_files = [f for f in glob.glob("services/execution/**/*.py", recursive=True) if not f.endswith("cli.py")]
    for fpath in exec_files:
        content = open(fpath, "r", encoding="utf-8").read()
        assert "RecoveryGroundTruth" not in content


@pytest.mark.asyncio
async def test_44_customer_id_preservation():
    """Test 44: Execution record strictly preserves target customer_id."""
    prop, target, gw = _create_authorized_triplet()
    service = ExecutionService()
    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))
    assert record.customer_id == target.customer_id


@pytest.mark.asyncio
async def test_45_transport_retry_does_not_increment_attempt_number():
    """Test 45: Replay does not increment attempt_number."""
    prop, target, gw = _create_authorized_triplet(attempts_count=1)
    service = ExecutionService()
    req = ExecutionRequest(proposal=prop, target=target, gateway_result=gw)

    rec1 = await service.execute_recovery(req)
    assert rec1.attempt_number == 2

    # Transport retry submission
    rec2 = await service.execute_recovery(req)
    assert rec2.attempt_number == 2  # Not incremented to 3!


def test_46_razorpay_key_empty_rejected():
    """Test 46: Empty key rejected in RazorpayTestProvider."""
    with pytest.raises(SecurityError):
        RazorpayTestProvider(key_id="", key_secret="secret")


def test_47_razorpay_secret_empty_rejected():
    """Test 47: Empty secret rejected in RazorpayTestProvider."""
    with pytest.raises(SecurityError):
        RazorpayTestProvider(key_id="rzp_test_123", key_secret="")


@pytest.mark.asyncio
async def test_48_audit_logger_query_by_execution_id():
    """Test 48: Audit logger correctly filters events by execution_id."""
    prop, target, gw = _create_authorized_triplet()
    service = ExecutionService()
    record = await service.execute_recovery(ExecutionRequest(proposal=prop, target=target, gateway_result=gw))

    events = service.audit_logger.get_events_for_execution(record.execution_id)
    assert len(events) >= 1
    assert all(e.execution_id == record.execution_id for e in events)


@pytest.mark.asyncio
async def test_49_different_proposals_produce_distinct_idempotency_keys():
    """Test 49: Different proposal IDs generate distinct idempotency keys."""
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    k1 = derive_execution_idempotency_key(p1, "v1", "v1", "RETRY_PAYMENT")
    k2 = derive_execution_idempotency_key(p2, "v1", "v1", "RETRY_PAYMENT")
    assert k1 != k2


@pytest.mark.asyncio
async def test_50_evaluator_correctly_records_failed_amounts():
    """Test 50: Evaluator accumulates failed amount when provider declines."""
    provider = MockPaymentProvider(default_outcome=ProviderNormalizedStatus.DECLINED)
    service = ExecutionService(provider=provider)
    evaluator = ExecutionEvaluator(service=service)

    triplets = [_create_authorized_triplet(amount_minor=50000)]
    records, report = await evaluator.evaluate_proposals(triplets)

    assert report.executions_failed == 1
    assert report.failed_amount_minor == 50000
    assert report.recovered_amount_minor == 0
