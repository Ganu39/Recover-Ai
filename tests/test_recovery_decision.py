"""Automated tests for RecoverAI Phase 5 Recovery Decision Agent."""

import uuid
import pytest

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from agents.decision import (
    DECISION_VERSION,
    DecisionInputContext,
    DecisionStatus,
    POLICY_VERSION,
    RecoveryActionType,
    RecoveryDecisionAgent,
    RecoveryDecisionEvaluator,
    RecoveryPolicy,
    derive_deterministic_proposal_id,
)
from agents.diagnosis.schemas import (
    AIDiagnosisResult,
    DiagnosisCategory,
    DiagnosisStatus,
    QualitativeConfidence,
)


def _create_sample_decision_context(
    target_type: str = "payment",
    amount_minor: int = 150000,
    history_count: int = 4,
    success_count: int = 4,
    attempts_count: int = 1,
    failure_code: str = "temporary_failure",
    subscription_status: str = None,
    ai_category: DiagnosisCategory = DiagnosisCategory.TRANSIENT_SYSTEM_ERROR,
    ai_recoverable: bool = True,
    ai_status: DiagnosisStatus = DiagnosisStatus.SUCCESS,
) -> DecisionInputContext:
    target_id = uuid.uuid4()
    case_id = uuid.uuid4()

    ai_diag = AIDiagnosisResult(
        prompt_version="v1",
        provider_name="mock_provider",
        model_name="mock-v1",
        latency_ms=15,
        status=ai_status,
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        amount_minor=amount_minor,
        currency="INR",
        diagnosis_category=ai_category,
        diagnosis_summary="Diagnostic inference summary",
        ai_recoverability_assessment=ai_recoverable if ai_status == DiagnosisStatus.SUCCESS else None,
        confidence=QualitativeConfidence.HIGH,
        ai_recoverability_reason="Reason for assessment",
    )

    return DecisionInputContext(
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        customer_id=uuid.uuid4(),
        amount_minor=amount_minor,
        currency="INR",
        amount_display=f"₹{amount_minor / 100:,.2f}",
        customer_history_count=history_count,
        customer_success_count=success_count,
        customer_success_rate_bps=(success_count * 10000) // history_count if history_count > 0 else 0,
        target_attempt_count=attempts_count,
        latest_failure_code=failure_code,
        subscription_status=subscription_status,
        ai_diagnosis=ai_diag,
    )


def test_1_temporary_failure_strong_history_proposes_retry():
    """Test 1: Proven history with transient failure proposes RETRY_PAYMENT / PROPOSED."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(history_count=5, success_count=5, attempts_count=1, failure_code="temporary_failure")

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.RETRY_PAYMENT
    assert prop.decision_status == DecisionStatus.PROPOSED
    assert prop.requires_human_approval is False


def test_2_insufficient_funds_proposes_retry_later_with_cooldown():
    """Test 2 (Correction 5): Insufficient funds proposes RETRY_LATER with cooldown_required=True."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=2, success_count=1, attempts_count=1, failure_code="insufficient_funds",
        ai_category=DiagnosisCategory.BALANCE_OR_LIMIT_DEFICIT
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.RETRY_LATER
    assert prop.decision_status == DecisionStatus.PROPOSED
    assert prop.cooldown_required is True
    assert prop.requires_human_approval is False


def test_3_expired_payment_method_proposes_update_link():
    """Test 3: Expired payment method proposes REQUEST_PAYMENT_METHOD_UPDATE."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=3, success_count=3, attempts_count=1, failure_code="expired_payment_method",
        ai_category=DiagnosisCategory.EXPIRED_OR_INVALID_METHOD
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE
    assert prop.decision_status == DecisionStatus.PROPOSED
    assert prop.requires_human_approval is False


def test_4_persistent_decline_proposes_no_action_blocked():
    """Test 4: Persistent decline on unproven history results in NO_ACTION."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=1, success_count=0, attempts_count=1, failure_code="generic_decline",
        ai_category=DiagnosisCategory.PERSISTENT_ISSUER_DECLINE, ai_recoverable=False
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.NO_ACTION
    assert prop.decision_status in (DecisionStatus.BLOCKED, DecisionStatus.NO_ACTION)


def test_5_exhausted_attempts_proposes_no_action_blocked():
    """Test 5: >= 3 attempts results strictly in NO_ACTION / BLOCKED."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=5, success_count=5, attempts_count=3, failure_code="temporary_failure"
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.NO_ACTION
    assert prop.decision_status == DecisionStatus.BLOCKED
    assert len(prop.blocking_conditions) > 0


def test_6_chronic_failure_history_proposes_no_action_blocked():
    """Test 6: Chronic failure history results strictly in NO_ACTION / BLOCKED."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=5, success_count=1, attempts_count=1, failure_code="generic_decline"
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.NO_ACTION
    assert prop.decision_status == DecisionStatus.BLOCKED


def test_7_subscription_past_due_proposes_subscription_workflow():
    """Test 7 (Correction 6): Past_due subscription proposes SUBSCRIPTION_RECOVERY_WORKFLOW."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        target_type="subscription", history_count=3, success_count=3, attempts_count=0,
        subscription_status="past_due", ai_category=DiagnosisCategory.SUBSCRIPTION_BILLING_ISSUE
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.SUBSCRIPTION_RECOVERY_WORKFLOW
    assert prop.decision_status == DecisionStatus.PROPOSED
    assert prop.requires_human_approval is False


def test_8_new_customer_temporary_failure_proposes_retry():
    """Test 8 (Correction 7): New customer with temporary error proposes RETRY_PAYMENT."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=0, success_count=0, attempts_count=1, failure_code="temporary_failure",
        ai_category=DiagnosisCategory.FIRST_TIME_USER_DROP
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.RETRY_PAYMENT
    assert prop.decision_status == DecisionStatus.PROPOSED


def test_9_new_customer_expired_method_proposes_update_link():
    """Test 9 (Correction 7): New customer with expired method proposes REQUEST_PAYMENT_METHOD_UPDATE."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=0, success_count=0, attempts_count=1, failure_code="expired_payment_method",
        ai_category=DiagnosisCategory.EXPIRED_OR_INVALID_METHOD
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE
    assert prop.decision_status == DecisionStatus.PROPOSED


def test_10_high_value_recoverable_escalates_to_human_review():
    """Test 10 (Correction 13): Order >= ₹5,000 escalates to HUMAN_REVIEW / REQUIRES_REVIEW."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        amount_minor=600000, history_count=5, success_count=5, attempts_count=1, failure_code="temporary_failure"
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.HUMAN_REVIEW
    assert prop.decision_status == DecisionStatus.REQUIRES_REVIEW
    assert prop.requires_human_approval is True


def test_11_high_value_plus_exhausted_attempts_strictly_blocked():
    """Test 11 (Correction 1): ₹50,000 + 4 attempts is BLOCKED / NO_ACTION (Precedence 1 over High Value)."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        amount_minor=5000000, history_count=5, success_count=5, attempts_count=4, failure_code="temporary_failure",
        ai_recoverable=True
    )

    prop = agent.evaluate_proposal(ctx)
    # Hard Block MUST take precedence over high value escalation!
    assert prop.action_type == RecoveryActionType.NO_ACTION
    assert prop.decision_status == DecisionStatus.BLOCKED
    assert prop.requires_human_approval is False


def test_12_high_value_plus_chronic_failure_strictly_blocked():
    """Test 12 (Correction 1): ₹25,000 + chronic failure is BLOCKED / NO_ACTION."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        amount_minor=2500000, history_count=5, success_count=1, attempts_count=1, failure_code="generic_decline",
        ai_recoverable=True
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.NO_ACTION
    assert prop.decision_status == DecisionStatus.BLOCKED


def test_13_ai_says_recoverable_but_policy_blocks_strictly_blocked():
    """Test 13 (Correction 1 & 4): Policy overrides AI recoverability recommendation."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=4, success_count=4, attempts_count=3, failure_code="temporary_failure",
        ai_recoverable=True
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.NO_ACTION
    assert prop.decision_status == DecisionStatus.BLOCKED


def test_14_ai_says_non_recoverable_but_deterministic_policy_governs():
    """Test 14: Deterministic policy governs action selection."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=4, success_count=4, attempts_count=1, failure_code="temporary_failure",
        ai_recoverable=False
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.RETRY_PAYMENT


def test_15_ai_unavailable_routes_safely():
    """Test 15 (Correction 13): AI provider error safely routes to HUMAN_REVIEW or policy fallback."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=1, success_count=0, attempts_count=1, failure_code="unknown_failure",
        ai_status=DiagnosisStatus.PROVIDER_ERROR
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.HUMAN_REVIEW
    assert prop.decision_status == DecisionStatus.REQUIRES_REVIEW
    assert prop.requires_human_approval is True


def test_16_ai_invalid_routes_safely():
    """Test 16: AI validation error routes safely without crashing."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=1, success_count=0, attempts_count=1, failure_code="unknown_failure",
        ai_status=DiagnosisStatus.VALIDATION_ERROR
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.HUMAN_REVIEW
    assert prop.decision_status == DecisionStatus.REQUIRES_REVIEW


def test_17_unknown_failure_routes_to_human_review():
    """Test 17: Unknown failure without history escalates to HUMAN_REVIEW."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(
        history_count=0, success_count=0, attempts_count=1, failure_code="unknown_failure",
        ai_status=DiagnosisStatus.PROVIDER_ERROR
    )

    prop = agent.evaluate_proposal(ctx)
    assert prop.action_type == RecoveryActionType.HUMAN_REVIEW
    assert prop.requires_human_approval is True


def test_18_ground_truth_air_gap_in_decision_context():
    """Test 18 (Correction 14): Verify DecisionInputContext contains zero ground truth fields."""
    ctx = _create_sample_decision_context()
    ctx_dict = ctx.model_dump()

    forbidden_keys = {"is_recoverable", "scenario_type", "expected_recovery_reason", "ground_truth"}
    for key in forbidden_keys:
        assert key not in ctx_dict


def test_19_no_financial_values_invented_by_ai():
    """Test 19 (Correction 10): Financial amounts strictly match observable amount_minor."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(amount_minor=349900)

    prop = agent.evaluate_proposal(ctx)
    assert prop.amount_minor == 349900
    assert prop.currency == "INR"


def test_20_integer_minor_units_money_safety():
    """Test 20 (Correction 10): Verify amount_minor is integer without float rounding."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(amount_minor=123456)

    prop = agent.evaluate_proposal(ctx)
    assert isinstance(prop.amount_minor, int)
    assert prop.amount_minor == 123456


def test_21_deterministic_proposal_id_generation():
    """Test 21 (Correction 2): Proposal ID is deterministically derived using uuid5."""
    target_id = uuid.uuid4()
    id1 = derive_deterministic_proposal_id("v1", "v1", "payment", target_id)
    id2 = derive_deterministic_proposal_id("v1", "v1", "payment", target_id)
    assert id1 == id2


def test_22_same_inputs_produce_identical_proposal():
    """Test 22 (Correction 2): Same inputs produce identical proposal output."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context()

    prop1 = agent.evaluate_proposal(ctx)
    prop2 = agent.evaluate_proposal(ctx)

    assert prop1.proposal_id == prop2.proposal_id
    assert prop1.action_type == prop2.action_type
    assert prop1.decision_status == prop2.decision_status


def test_23_different_policy_version_produces_distinct_proposal_id():
    """Test 23 (Correction 2 & 15): Different policy version produces distinct proposal ID."""
    target_id = uuid.uuid4()
    id1 = derive_deterministic_proposal_id("v1", "v1", "payment", target_id)
    id2 = derive_deterministic_proposal_id("v1", "v2", "payment", target_id)
    assert id1 != id2


def test_24_retry_limit_enforcement_invariants():
    """Test 24: Max retry limit (2) strictly blocks attempts >= 3."""
    agent = RecoveryDecisionAgent(policy=RecoveryPolicy(max_retry_attempts=2))
    for att in [3, 4, 5]:
        ctx = _create_sample_decision_context(attempts_count=att)
        prop = agent.evaluate_proposal(ctx)
        assert prop.action_type == RecoveryActionType.NO_ACTION
        assert prop.decision_status == DecisionStatus.BLOCKED


def test_25_human_review_enforcement_invariants():
    """Test 25: All REQUIRES_REVIEW proposals strictly require human approval."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context(amount_minor=1000000)
    prop = agent.evaluate_proposal(ctx)
    assert prop.decision_status == DecisionStatus.REQUIRES_REVIEW
    assert prop.requires_human_approval is True


def test_26_execution_boundary_integrity():
    """Test 26 (Correction 17): Proposal contains zero execution capability or boolean execution flags."""
    agent = RecoveryDecisionAgent()
    ctx = _create_sample_decision_context()
    prop = agent.evaluate_proposal(ctx)

    assert not hasattr(prop, "execute")
    assert not hasattr(prop, "execute_now")
    assert not hasattr(prop, "gateway_call")
    assert not hasattr(prop, "send_notification")


@pytest.mark.asyncio
async def test_27_end_to_end_decision_evaluator_on_synthetic_dataset():
    """Test 27: End-to-end evaluation on synthetic dataset produces verified report."""
    config = GeneratorConfig(seed=42, num_customers=25, num_payments=60)
    dataset = SyntheticDataGenerator(config).generate()

    evaluator = RecoveryDecisionEvaluator()
    report = await evaluator.evaluate_dataset(dataset)

    assert report.decision_version == DECISION_VERSION
    assert report.policy_version == POLICY_VERSION
    assert report.evaluated_proposals_count == len(dataset.observable.recovery_cases)
    assert report.unsafe_action_proposal_count == 0
    assert report.total_amount_at_risk_minor > 0
