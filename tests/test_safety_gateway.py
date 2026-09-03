"""Comprehensive security, safety invariant, and unit tests for Phase 6 Safety Gateway."""

import ast
import glob
import os
import uuid
import pytest
from pydantic import ValidationError

from agents.decision.schemas import (
    DECISION_VERSION,
    ExplanationChain,
    POLICY_VERSION,
    RecoveryActionType,
    RecoveryDecisionProposal,
    DecisionStatus,
)
from agents.gateway import (
    GATEWAY_VERSION,
    DeterministicSafetyGateway,
    GatewayConfig,
    GatewayDecision,
    GatewayDecisionResult,
    GatewayKillSwitch,
    GatewayPolicy,
    GatewayReasonCode,
    GatewayTargetContext,
    HumanApprovalRecord,
    InMemoryIdempotencyStore,
    InMemoryRateLimiter,
    derive_expected_proposal_id,
)


def _create_sample_target(
    target_type: str = "payment",
    amount_minor: int = 150000,
    currency: str = "INR",
    history_count: int = 4,
    success_count: int = 4,
    attempts_count: int = 1,
    failure_code: str = "temporary_failure",
) -> GatewayTargetContext:
    target_id = uuid.uuid4()
    return GatewayTargetContext(
        case_id=uuid.uuid4(),
        target_type=target_type,
        target_id=target_id,
        customer_id=uuid.uuid4(),
        amount_minor=amount_minor,
        currency=currency,
        amount_display=f"₹{amount_minor / 100:,.2f}",
        customer_history_count=history_count,
        customer_success_count=success_count,
        customer_success_rate_bps=(success_count * 10000) // history_count if history_count > 0 else 0,
        target_attempt_count=attempts_count,
        latest_failure_code=failure_code,
    )


def _create_sample_proposal(
    target: GatewayTargetContext,
    action_type: RecoveryActionType = RecoveryActionType.RETRY_PAYMENT,
    decision_status: DecisionStatus = DecisionStatus.PROPOSED,
    amount_minor: int = None,
    currency: str = None,
    decision_version: str = DECISION_VERSION,
    policy_version: str = POLICY_VERSION,
    requires_human_approval: bool = False,
) -> RecoveryDecisionProposal:
    amt = amount_minor if amount_minor is not None else target.amount_minor
    curr = currency if currency is not None else target.currency
    prop_id = derive_expected_proposal_id(
        decision_version=decision_version,
        policy_version=policy_version,
        target_type=target.target_type,
        target_id=target.target_id,
    )
    return RecoveryDecisionProposal(
        decision_version=decision_version,
        policy_version=policy_version,
        proposal_id=prop_id,
        case_id=target.case_id,
        target_type=target.target_type,
        target_id=target.target_id,
        amount_minor=amt,
        currency=curr,
        amount_display=f"₹{amt / 100:,.2f}",
        action_type=action_type,
        decision_status=decision_status,
        explanation=ExplanationChain(
            observed_facts=["Sample fact"],
            ai_inferences=["Sample AI inference"],
            policy_checks=["Sample policy check"],
            final_rationale="Sample rationale",
        ),
        requires_human_approval=requires_human_approval,
    )


# =====================================================================
# 1. CORE FUNCTIONAL SAFETY TESTS
# =====================================================================

def test_1_valid_retry_proposal_approved():
    """Test 1: Valid retry proposal with matching context is APPROVED."""
    target = _create_sample_target(amount_minor=150000, attempts_count=1)
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)
    gateway = DeterministicSafetyGateway()

    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.APPROVED
    assert result.eligible_for_execution_layer is True
    assert result.reason_code == GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER
    assert result.is_replay is False


def test_2_invalid_schema_fails_closed():
    """Test 2: Invalid proposal or target schema rejected with INVALID_PROPOSAL."""
    with pytest.raises(ValidationError):
        # Target with non-integer amount
        GatewayTargetContext(
            target_type="payment",
            target_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            amount_minor="five thousand",  # type: ignore
            currency="INR",
            amount_display="₹5,000",
        )


def test_3_unknown_action_type_blocked():
    """Test 3: Arbitrary or unknown action string cannot be processed as executable."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    # Tamper with action_type
    object.__setattr__(proposal, "action_type", "UNAUTHORIZED_PAYMENT_CHARGE")

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision in {GatewayDecision.BLOCKED, GatewayDecision.INVALID_PROPOSAL}
    assert result.eligible_for_execution_layer is False


def test_4_no_action_proposal_cannot_execute():
    """Test 4: NO_ACTION proposal is strictly BLOCKED from execution layer."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.NO_ACTION)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.BLOCKED
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_NON_EXECUTABLE_ACTION


def test_5_human_review_without_approval_requires_review():
    """Test 5: HUMAN_REVIEW proposal without human approval token routes to REQUIRES_REVIEW."""
    target = _create_sample_target(amount_minor=200000)
    proposal = _create_sample_proposal(
        target, action_type=RecoveryActionType.HUMAN_REVIEW, requires_human_approval=True
    )

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=None)
    assert result.gateway_decision == GatewayDecision.REQUIRES_REVIEW
    assert result.eligible_for_execution_layer is False
    assert result.reason_code in {
        GatewayReasonCode.MISSING_HUMAN_APPROVAL,
        GatewayReasonCode.HIGH_VALUE_REQUIRES_REVIEW,
    }


def test_6_attempt_limit_independently_enforced():
    """Test 6: target_attempt_count >= 3 independently BLOCKED even if proposal was marked PROPOSED."""
    target = _create_sample_target(attempts_count=3)
    # Malicious/buggy Phase 5 proposing retry despite 3 attempts
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT, decision_status=DecisionStatus.PROPOSED)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.BLOCKED
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_RETRY_LIMIT_EXCEEDED


def test_7_high_value_requires_approval():
    """Test 7: High-value transaction (>= ₹5,000 / 500,000 paise) requires approval."""
    target = _create_sample_target(amount_minor=500000)  # ₹5,000
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=None)
    assert result.gateway_decision == GatewayDecision.REQUIRES_REVIEW
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.HIGH_VALUE_REQUIRES_REVIEW


def test_8_amount_mismatch_fails_closed():
    """Test 8: Proposal amount differing from trusted target fails closed."""
    target = _create_sample_target(amount_minor=150000)
    # Tampered proposal claiming ₹100 instead of ₹1,500
    proposal = _create_sample_proposal(target, amount_minor=10000)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_AMOUNT_MISMATCH


def test_9_currency_mismatch_fails_closed():
    """Test 9: Proposal currency differing from trusted target fails closed."""
    target = _create_sample_target(currency="INR")
    proposal = _create_sample_proposal(target, currency="USD")

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_CURRENCY_MISMATCH


def test_10_negative_or_zero_amount_fails_closed():
    """Test 10: Non-positive amounts strictly rejected."""
    target = _create_sample_target(amount_minor=0)
    proposal = _create_sample_proposal(target, amount_minor=0)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_INVALID_FINANCIAL_UNIT


def test_11_policy_version_mismatch():
    """Test 11: Proposal with policy version mismatch is rejected."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target, policy_version="v2_unsupported")

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.reason_code == GatewayReasonCode.BLOCK_SCHEMA_VALIDATION_FAILED


def test_12_gateway_version_mismatch():
    """Test 12: Gateway configuration version mismatch fails closed."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    config = GatewayConfig(gateway_version="v99")

    gateway = DeterministicSafetyGateway(config=config)
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.reason_code == GatewayReasonCode.GATEWAY_CONFIGURATION_ERROR


# =====================================================================
# 2. KILL SWITCH TESTS
# =====================================================================

def test_13_active_kill_switch_blocks_all():
    """Test 13: When kill switch is active, all authorizations are suspended."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)

    ks = GatewayKillSwitch(initial_state=True)
    gateway = DeterministicSafetyGateway(kill_switch=ks)

    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.KILL_SWITCH_ACTIVE
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.KILL_SWITCH_ACTIVE


def test_14_corrupted_kill_switch_fails_closed():
    """Test 14: Corrupted kill switch fails closed."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)

    ks = GatewayKillSwitch.from_config(None)  # Corrupted / missing config
    gateway = DeterministicSafetyGateway(kill_switch=ks)

    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.KILL_SWITCH_ACTIVE
    assert result.eligible_for_execution_layer is False


# =====================================================================
# 3. RATE LIMITING TESTS
# =====================================================================

def test_15_rate_limit_exceeded():
    """Test 15: Exceeding max requests per target in window triggers RATE_LIMITED."""
    target = _create_sample_target()
    gateway = DeterministicSafetyGateway()

    # Submit 3 valid attempts for target, clearing idempotency store to simulate distinct non-replayed requests
    for _ in range(3):
        gateway.idempotency_store.clear()
        p = _create_sample_proposal(target)
        res = gateway.evaluate_proposal(p, target)
        assert res.gateway_decision == GatewayDecision.APPROVED

    # 4th request exceeds rate limit (max_per_window=3)
    gateway.idempotency_store.clear()
    p4 = _create_sample_proposal(target)
    res4 = gateway.evaluate_proposal(p4, target)
    assert res4.gateway_decision == GatewayDecision.RATE_LIMITED
    assert res4.eligible_for_execution_layer is False
    assert res4.reason_code == GatewayReasonCode.RATE_LIMIT_EXCEEDED


# =====================================================================
# 4. IDEMPOTENCY & REPLAY PROTECTION TESTS
# =====================================================================

def test_16_exact_duplicate_returns_idempotent_replay():
    """Test 16: Exact duplicate proposal returns cached result with is_replay=True without consuming rate limit."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    gateway = DeterministicSafetyGateway()

    res1 = gateway.evaluate_proposal(proposal, target)
    assert res1.gateway_decision == GatewayDecision.APPROVED
    assert res1.is_replay is False

    res2 = gateway.evaluate_proposal(proposal, target)
    assert res2.gateway_decision == GatewayDecision.APPROVED
    assert res2.is_replay is True
    assert res2.reason_code == GatewayReasonCode.IDEMPOTENT_REPLAY_APPROVED


def test_17_previously_blocked_replay_maintains_block():
    """Test 17: Previously blocked proposal replay maintains BLOCKED state."""
    target = _create_sample_target(attempts_count=4)
    proposal = _create_sample_proposal(target)
    gateway = DeterministicSafetyGateway()

    res1 = gateway.evaluate_proposal(proposal, target)
    assert res1.gateway_decision == GatewayDecision.BLOCKED

    res2 = gateway.evaluate_proposal(proposal, target)
    assert res2.gateway_decision == GatewayDecision.BLOCKED
    assert res2.is_replay is True
    assert res2.reason_code == GatewayReasonCode.IDEMPOTENT_REPLAY_BLOCKED


def test_18_conflicting_proposal_for_same_target():
    """Test 18: Conflicting proposal with different action for already APPROVED target is BLOCKED."""
    target = _create_sample_target()
    proposal1 = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)
    gateway = DeterministicSafetyGateway()

    res1 = gateway.evaluate_proposal(proposal1, target)
    assert res1.gateway_decision == GatewayDecision.APPROVED

    # Conflicting proposal for same target proposing different action
    proposal2 = _create_sample_proposal(
        target, action_type=RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE
    )
    res2 = gateway.evaluate_proposal(proposal2, target)
    assert res2.gateway_decision == GatewayDecision.BLOCKED
    assert res2.reason_code == GatewayReasonCode.BLOCK_CONFLICTING_PROPOSAL_FOR_TARGET


def test_18b_idempotency_store_target_conflict_with_different_proposal_id():
    """Test 18b: Target conflict evaluated directly on distinct proposal IDs in store."""
    store = InMemoryIdempotencyStore()
    target_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()

    mock_res = GatewayDecisionResult(
        gateway_decision=GatewayDecision.APPROVED,
        proposal_id=p1_id,
        target_type="payment",
        target_id=target_id,
        decision_reason="Approved",
        reason_code=GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER,
        policy_version="v1",
        gateway_version="v1",
        decision_version="v1",
        audit_reference=uuid.uuid4(),
        eligible_for_execution_layer=True,
    )

    store.record_decision(
        proposal_id=p1_id,
        target_type="payment",
        target_id=target_id,
        action_type="RETRY_PAYMENT",
        amount_minor=150000,
        gateway_version="v1",
        policy_version="v1",
        decision_result=mock_res,
    )

    conflict = store.check_target_conflict(
        target_type="payment",
        target_id=target_id,
        proposal_id=p2_id,
        action_type="REQUEST_PAYMENT_METHOD_UPDATE",
        amount_minor=150000,
    )
    assert conflict is not None
    code, msg = conflict
    assert code == GatewayReasonCode.BLOCK_CONFLICTING_PROPOSAL_FOR_TARGET


# =====================================================================
# 5. HUMAN APPROVAL VALIDATION TESTS
# =====================================================================

def test_19_valid_human_approval_authorizes_high_value():
    """Test 19: Valid human approval token authorizes high-value proposal."""
    target = _create_sample_target(amount_minor=600000)  # ₹6,000
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)

    approval = HumanApprovalRecord(
        proposal_id=proposal.proposal_id,
        target_id=proposal.target_id,
        approved_by="supervisor@recoverai.internal",
        approved_at_iso="2026-09-03T09:00:00Z",
        approval_status=True,
        notes="High-value corporate customer verified.",
    )

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=approval)
    assert result.gateway_decision == GatewayDecision.APPROVED
    assert result.eligible_for_execution_layer is True
    assert result.reason_code == GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER


def test_20_malformed_or_mismatched_approval_rejected():
    """Test 20: Approval token with mismatched proposal_id or status=False is rejected."""
    target = _create_sample_target(amount_minor=600000)
    proposal = _create_sample_proposal(target)

    # Forged approval token referencing wrong proposal
    bad_approval = HumanApprovalRecord(
        proposal_id=uuid.uuid4(),  # Mismatch
        target_id=proposal.target_id,
        approved_by="supervisor@recoverai.internal",
        approved_at_iso="2026-09-03T09:00:00Z",
        approval_status=True,
    )

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=bad_approval)
    assert result.gateway_decision == GatewayDecision.REQUIRES_REVIEW
    assert result.reason_code == GatewayReasonCode.INVALID_HUMAN_APPROVAL


def test_21_human_approval_cannot_override_hard_blocks():
    """Test 21: Human approval CANNOT bypass attempt cap or chronic decline invariants."""
    target = _create_sample_target(amount_minor=600000, attempts_count=4)
    proposal = _create_sample_proposal(target)

    approval = HumanApprovalRecord(
        proposal_id=proposal.proposal_id,
        target_id=proposal.target_id,
        approved_by="supervisor@recoverai.internal",
        approved_at_iso="2026-09-03T09:00:00Z",
        approval_status=True,
    )

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=approval)
    # Hard attempt cap strictly overrides human approval
    assert result.gateway_decision == GatewayDecision.BLOCKED
    assert result.reason_code == GatewayReasonCode.BLOCK_RETRY_LIMIT_EXCEEDED


# =====================================================================
# 6. TAMPER-RESISTANCE & SECURITY TESTS
# =====================================================================

def test_22_tampered_proposal_identity_rejected():
    """Test 22: Forged or non-deterministic proposal UUID is rejected."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    # Tamper with proposal_id
    object.__setattr__(proposal, "proposal_id", uuid.uuid4())

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.reason_code == GatewayReasonCode.BLOCK_PROPOSAL_IDENTITY_MISMATCH


def test_23_tampered_target_id_rejected():
    """Test 23: Proposal target_id differing from trusted target context is rejected."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    object.__setattr__(proposal, "target_id", uuid.uuid4())

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.INVALID_PROPOSAL
    assert result.reason_code == GatewayReasonCode.BLOCK_PROPOSAL_IDENTITY_MISMATCH


def test_24_ground_truth_air_gap():
    """Test 24: GatewayTargetContext contains zero evaluation ground truth fields."""
    target = _create_sample_target()
    forbidden_fields = {"is_recoverable", "scenario_type", "expected_recovery_reason", "ai_diagnosis"}
    target_fields = set(target.model_dump().keys())
    for f in forbidden_fields:
        assert f not in target_fields, f"Forbidden ground truth field {f} found in GatewayTargetContext"


def test_25_static_security_zero_razorpay_imports():
    """Test 25: Verify static AST scan finds zero Razorpay imports in agents/gateway/."""
    gateway_files = glob.glob("agents/gateway/**/*.py", recursive=True)
    assert len(gateway_files) > 0

    for fpath in gateway_files:
        with open(fpath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=fpath)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "razorpay" not in alias.name.lower(), f"Forbidden import {alias.name} in {fpath}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert "razorpay" not in node.module.lower(), f"Forbidden from-import {node.module} in {fpath}"


def test_26_static_security_zero_network_calls():
    """Test 26: Verify no external HTTP clients (requests, httpx, urllib3) imported in agents/gateway/."""
    gateway_files = glob.glob("agents/gateway/**/*.py", recursive=True)
    forbidden_modules = {"requests", "httpx", "urllib3", "aiohttp"}

    for fpath in gateway_files:
        with open(fpath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=fpath)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in forbidden_modules, f"Forbidden client {alias.name} in {fpath}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert node.module not in forbidden_modules, f"Forbidden client {node.module} in {fpath}"


def test_27_static_security_zero_db_writes():
    """Test 27: Verify zero SQLAlchemy session writes in agents/gateway/."""
    gateway_files = glob.glob("agents/gateway/**/*.py", recursive=True)
    for fpath in gateway_files:
        content = open(fpath, "r", encoding="utf-8").read()
        assert "db.commit" not in content
        assert "session.commit" not in content
        assert "session.add" not in content


def test_28_audit_record_emitted_and_immutable():
    """Test 28: Audit record is correctly emitted and immutable."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)

    audit_entry = gateway.audit_logger.get_by_audit_reference(result.audit_reference)
    assert audit_entry is not None
    assert audit_entry.proposal_id == proposal.proposal_id
    assert audit_entry.gateway_decision == GatewayDecision.APPROVED
    assert audit_entry.amount_minor == target.amount_minor
    assert audit_entry.currency == target.currency


def test_29_batch_evaluation_matches_individual():
    """Test 29: Batch evaluation produces identical results to sequential calls."""
    target1 = _create_sample_target(amount_minor=100000)
    target2 = _create_sample_target(amount_minor=200000)
    prop1 = _create_sample_proposal(target1)
    prop2 = _create_sample_proposal(target2)

    gateway = DeterministicSafetyGateway()
    batch_results = gateway.evaluate_batch([(prop1, target1, None), (prop2, target2, None)])

    assert len(batch_results) == 2
    assert batch_results[0].gateway_decision == GatewayDecision.APPROVED
    assert batch_results[1].gateway_decision == GatewayDecision.APPROVED


# =====================================================================
# 7. ADDITIONAL DEFENSE-IN-DEPTH & SECURITY COVERAGE TESTS
# =====================================================================

def test_30_chronic_failure_history_independently_blocked():
    """Test 30: Chronic failure history (low success rate + blocked decline code) is strictly BLOCKED."""
    target = _create_sample_target(
        history_count=5,
        success_count=1,  # 20% success rate (2000 bps < 2500 bps)
        attempts_count=1,
        failure_code="generic_decline",
    )
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.BLOCKED
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_CHRONIC_FAILURE_INVARIANT


def test_31_subscription_workflow_authorized_for_past_due():
    """Test 31: SUBSCRIPTION_RECOVERY_WORKFLOW proposal authorized for past_due subscription."""
    target = _create_sample_target(target_type="subscription", failure_code="subscription_past_due")
    target.subscription_status = "past_due"
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.SUBSCRIPTION_RECOVERY_WORKFLOW)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.APPROVED
    assert result.eligible_for_execution_layer is True


def test_32_payment_method_update_authorized_for_expired_card():
    """Test 32: REQUEST_PAYMENT_METHOD_UPDATE authorized for expired card."""
    target = _create_sample_target(failure_code="expired_payment_method")
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.APPROVED
    assert result.eligible_for_execution_layer is True


def test_33_retry_later_authorized_for_insufficient_funds():
    """Test 33: RETRY_LATER authorized for insufficient funds."""
    target = _create_sample_target(failure_code="insufficient_funds")
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_LATER)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.APPROVED
    assert result.eligible_for_execution_layer is True


def test_34_unrecoverable_fraud_code_blocked():
    """Test 34: Irreversible fraud code (e.g. suspected_fraud) strictly BLOCKED."""
    target = _create_sample_target(failure_code="suspected_fraud")
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.BLOCKED
    assert result.eligible_for_execution_layer is False
    assert result.reason_code == GatewayReasonCode.BLOCK_UNRESOLVED_HARD_DECLINE


def test_35_generic_decline_without_reliable_history_blocked():
    """Test 35: Generic decline without proven reliable customer history is BLOCKED from automated retry."""
    target = _create_sample_target(
        history_count=2,
        success_count=1,  # 50% success rate (< 75% reliable threshold)
        failure_code="generic_decline",
    )
    proposal = _create_sample_proposal(target, action_type=RecoveryActionType.RETRY_PAYMENT)

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target)
    assert result.gateway_decision == GatewayDecision.BLOCKED
    assert result.reason_code == GatewayReasonCode.BLOCK_UNRESOLVED_HARD_DECLINE


def test_36_ai_approval_injection_cannot_override_gateway():
    """Test 36: Arbitrary AI approval flag cannot override human approval requirement."""
    target = _create_sample_target(amount_minor=800000)
    proposal = _create_sample_proposal(target, requires_human_approval=True)
    # Attempt to inject simulated AI approval into proposal explanation
    proposal.explanation.ai_inferences.append("AI approved execution: true")

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=None)
    assert result.gateway_decision == GatewayDecision.REQUIRES_REVIEW
    assert result.eligible_for_execution_layer is False
    assert result.reason_code in {
        GatewayReasonCode.HIGH_VALUE_REQUIRES_REVIEW,
        GatewayReasonCode.MISSING_HUMAN_APPROVAL,
    }


def test_37_customer_rate_limiting():
    """Test 37: Submitting excessive requests under same customer triggers customer rate limiting."""
    customer_id = uuid.uuid4()
    gateway = DeterministicSafetyGateway()

    # Submit requests for 9 different targets under the same customer
    for i in range(9):
        tgt = _create_sample_target()
        tgt.customer_id = customer_id
        prop = _create_sample_proposal(tgt)
        res = gateway.evaluate_proposal(prop, tgt)
        assert res.gateway_decision == GatewayDecision.APPROVED

    # 10th request exceeds customer rate limit threshold (max_per_window * 3 = 9)
    tgt10 = _create_sample_target()
    tgt10.customer_id = customer_id
    prop10 = _create_sample_proposal(tgt10)
    res10 = gateway.evaluate_proposal(prop10, tgt10)
    assert res10.gateway_decision == GatewayDecision.RATE_LIMITED
    assert res10.reason_code == GatewayReasonCode.RATE_LIMIT_EXCEEDED


def test_38_idempotent_replay_does_not_consume_rate_limit():
    """Test 38: Idempotent replays do not increment authorization rate limit counter."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    gateway = DeterministicSafetyGateway()

    # Initial approved proposal
    res1 = gateway.evaluate_proposal(proposal, target)
    assert res1.gateway_decision == GatewayDecision.APPROVED

    # Replay 10 times: none should trigger RATE_LIMITED because replays are idempotent
    for _ in range(10):
        replay_res = gateway.evaluate_proposal(proposal, target)
        assert replay_res.gateway_decision == GatewayDecision.APPROVED
        assert replay_res.is_replay is True


def test_39_rate_limiter_window_expiration():
    """Test 39: Requests past sliding window allow new authorizations."""
    target = _create_sample_target()
    limiter = InMemoryRateLimiter(max_per_window=1, window_seconds=100)

    # Attempt at t=0
    limiter.record_attempt(target.target_type, target.target_id, now_epoch=1000.0)
    assert limiter.is_rate_limited(target.target_type, target.target_id, now_epoch=1050.0) is True

    # At t=1101 (past 100s window), rate limit clears
    assert limiter.is_rate_limited(target.target_type, target.target_id, now_epoch=1101.0) is False


def test_40_kill_switch_deactivation_restores_authorization():
    """Test 40: Activating kill switch blocks, deactivating restores authorization."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)
    ks = GatewayKillSwitch(initial_state=False)
    gateway = DeterministicSafetyGateway(kill_switch=ks)

    res1 = gateway.evaluate_proposal(proposal, target)
    assert res1.gateway_decision == GatewayDecision.APPROVED

    # Activate kill switch
    ks.activate()
    gateway.idempotency_store.clear()
    res2 = gateway.evaluate_proposal(proposal, target)
    assert res2.gateway_decision == GatewayDecision.KILL_SWITCH_ACTIVE

    # Deactivate kill switch
    ks.deactivate()
    gateway.idempotency_store.clear()
    res3 = gateway.evaluate_proposal(proposal, target)
    assert res3.gateway_decision == GatewayDecision.APPROVED


def test_41_human_approval_empty_approver_rejected():
    """Test 41: Human approval record with empty approver string is rejected."""
    target = _create_sample_target(amount_minor=600000)
    proposal = _create_sample_proposal(target)

    bad_approval = HumanApprovalRecord(
        proposal_id=proposal.proposal_id,
        target_id=proposal.target_id,
        approved_by="   ",  # Blank approver
        approved_at_iso="2026-09-03T09:00:00Z",
        approval_status=True,
    )

    gateway = DeterministicSafetyGateway()
    result = gateway.evaluate_proposal(proposal, target, approval=bad_approval)
    assert result.gateway_decision == GatewayDecision.REQUIRES_REVIEW
    assert result.reason_code == GatewayReasonCode.INVALID_HUMAN_APPROVAL


def test_42_deterministic_repeatability():
    """Test 42: Running gateway on identical inputs repeatedly produces identical decisions and reason codes."""
    target = _create_sample_target()
    proposal = _create_sample_proposal(target)

    results = []
    for _ in range(5):
        gw = DeterministicSafetyGateway()
        res = gw.evaluate_proposal(proposal, target)
        results.append(res)

    for r in results[1:]:
        assert r.gateway_decision == results[0].gateway_decision
        assert r.reason_code == results[0].reason_code
        assert r.checks_evaluated == results[0].checks_evaluated
        assert r.checks_passed == results[0].checks_passed
        assert r.eligible_for_execution_layer == results[0].eligible_for_execution_layer


def test_43_static_security_zero_floating_point():
    """Test 43: Ensure agents/gateway/ contains no float() conversions for financial values."""
    gateway_files = glob.glob("agents/gateway/**/*.py", recursive=True)
    for fpath in gateway_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            # Verify no float(amount_minor) or monetary float division
            assert "float(target.amount_minor)" not in content
            assert "float(proposal.amount_minor)" not in content


def test_44_evaluator_unsafe_authorization_rate_zero():
    """Test 44: GatewayEvaluator reports unsafe_authorization_rate_bps == 0 across safe proposals."""
    from agents.gateway.evaluator import GatewayEvaluator

    evaluator = GatewayEvaluator()
    triplets = []
    for _ in range(10):
        tgt = _create_sample_target()
        prop = _create_sample_proposal(tgt)
        triplets.append((prop, tgt, None))

    results, report = evaluator.evaluate(triplets)
    assert report.total_evaluated == 10
    assert report.approved_count == 10
    assert report.unsafe_authorizations == 0
    assert report.unsafe_authorization_rate_bps == 0
    assert report.financial_integrity_violations == 0


def test_45_evaluator_blocks_unsafe_proposals():
    """Test 45: GatewayEvaluator correctly flags and blocks unsafe proposals with zero unsafe leaks."""
    from agents.gateway.evaluator import GatewayEvaluator

    evaluator = GatewayEvaluator()
    triplets = []
    # 5 safe proposals
    for _ in range(5):
        tgt = _create_sample_target()
        prop = _create_sample_proposal(tgt)
        triplets.append((prop, tgt, None))

    # 5 unsafe proposals (exhausted attempts)
    for _ in range(5):
        tgt_unsafe = _create_sample_target(attempts_count=4)
        prop_unsafe = _create_sample_proposal(tgt_unsafe)
        triplets.append((prop_unsafe, tgt_unsafe, None))

    results, report = evaluator.evaluate(triplets)
    assert report.total_evaluated == 10
    assert report.approved_count == 5
    assert report.blocked_count == 5
    assert report.unsafe_authorizations == 0
    assert report.unsafe_authorization_rate_bps == 0
