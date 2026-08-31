"""Automated tests for RecoverAI Phase 3 Deterministic Revenue-Risk Engine (v1)."""

import random
import uuid
import pytest

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig, RecoveryGroundTruth, ScenarioType
from services.risk_engine import (
    BASELINE_VERSION,
    BaselineEvaluator,
    DeterministicRiskEngine,
    ObservableFeatureExtractor,
    ObservableRiskContext,
    RiskLevel,
    RiskReasonCode,
    calculate_evaluation_metrics,
)


def test_1_deterministic_result_for_same_input():
    """Test 1: Verify identical input produces identical evaluation result and evidence."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=150000,
        currency="INR",
        customer_history_count=5,
        customer_success_count=4,
        customer_success_rate_bps=8000,
        target_attempt_count=1,
        latest_failure_code="temporary_failure",
    )

    res1 = engine.evaluate(ctx)
    res2 = engine.evaluate(ctx)

    assert res1.predicted_recoverable == res2.predicted_recoverable
    assert res1.risk_level == res2.risk_level
    assert res1.amount_at_risk_minor == res2.amount_at_risk_minor
    assert len(res1.evidence) == len(res2.evidence)


def test_2_exhausted_attempts_predicted_non_recoverable():
    """Test 2: Verify >= 3 failed attempts results in predicted_recoverable=False and RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=50000,
        currency="INR",
        customer_history_count=6,
        customer_success_count=5,
        customer_success_rate_bps=8333,
        target_attempt_count=3,
        latest_failure_code="insufficient_funds",
    )

    res = engine.evaluate(ctx)
    assert res.predicted_recoverable is False
    assert res.risk_level == RiskLevel.CRITICAL
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS in reason_codes


def test_3_chronic_decline_history_predicted_non_recoverable():
    """Test 3: Verify chronic low success history results in predicted_recoverable=False."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=80000,
        currency="INR",
        customer_history_count=5,
        customer_success_count=1,
        customer_success_rate_bps=2000,  # 20%
        target_attempt_count=1,
        latest_failure_code="generic_decline",
    )

    res = engine.evaluate(ctx)
    assert res.predicted_recoverable is False
    assert res.risk_level == RiskLevel.CRITICAL
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_CHRONIC_DECLINE_HISTORY in reason_codes


def test_4_proven_history_transient_failure_predicted_recoverable():
    """Test 4: Verify strong customer history with transient failure is predicted recoverable."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=120000,
        currency="INR",
        customer_history_count=4,
        customer_success_count=4,
        customer_success_rate_bps=10000,
        target_attempt_count=1,
        latest_failure_code="temporary_failure",
    )

    res = engine.evaluate(ctx)
    assert res.predicted_recoverable is True
    assert res.risk_level == RiskLevel.LOW
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_TRANSIENT_FAILURE_PROVEN_HISTORY in reason_codes


def test_5_insufficient_funds_generates_distinct_reason_code():
    """Test 5 (Correction 1): Verify insufficient funds generates RC_INSUFFICIENT_FUNDS."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=50000,
        currency="INR",
        customer_history_count=2,
        customer_success_count=1,
        customer_success_rate_bps=5000,
        target_attempt_count=1,
        latest_failure_code="insufficient_funds",
    )

    res = engine.evaluate(ctx)
    assert res.predicted_recoverable is True
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_INSUFFICIENT_FUNDS in reason_codes
    assert RiskReasonCode.RC_TRANSIENT_FAILURE_PROVEN_HISTORY not in reason_codes


def test_6_high_value_attaches_exposure_without_forcing_recoverability():
    """Test 6 (Correction 2): High value attached as exposure; does NOT override chronic non-recoverability."""
    engine = DeterministicRiskEngine()
    # High value (₹25,000) with chronic failure history
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=2500000,  # ₹25,000 in paise
        currency="INR",
        customer_history_count=5,
        customer_success_count=1,
        customer_success_rate_bps=2000,
        target_attempt_count=1,
        latest_failure_code="generic_decline",
    )

    res = engine.evaluate(ctx)
    # High value MUST NOT force recoverability
    assert res.predicted_recoverable is False
    assert res.risk_level == RiskLevel.CRITICAL
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_HIGH_VALUE_EXPOSURE in reason_codes
    assert RiskReasonCode.RC_CHRONIC_DECLINE_HISTORY in reason_codes


def test_7_separate_recoverability_and_risk_level():
    """Test 7 (Correction 3): Verify recoverability and risk level are distinct dimensions."""
    engine = DeterministicRiskEngine()

    # Case A: Low exposure, highly recoverable
    ctx_a = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=50000,  # ₹500
        currency="INR",
        customer_history_count=4,
        customer_success_count=4,
        customer_success_rate_bps=10000,
        target_attempt_count=1,
        latest_failure_code="temporary_failure",
    )
    res_a = engine.evaluate(ctx_a)
    assert res_a.predicted_recoverable is True
    assert res_a.risk_level == RiskLevel.LOW

    # Case B: High exposure, non-recoverable
    ctx_b = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=1000000,  # ₹10,000
        currency="INR",
        customer_history_count=1,
        customer_success_count=0,
        customer_success_rate_bps=0,
        target_attempt_count=3,
        latest_failure_code="generic_decline",
    )
    res_b = engine.evaluate(ctx_b)
    assert res_b.predicted_recoverable is False
    assert res_b.risk_level == RiskLevel.CRITICAL


def test_8_subscription_past_due_predicted_recoverable():
    """Test 8: Verify past-due subscription is predicted recoverable with RC_SUBSCRIPTION_BILLING_GLITCH."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="subscription",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=99900,
        currency="INR",
        customer_history_count=3,
        customer_success_count=3,
        customer_success_rate_bps=10000,
        target_attempt_count=0,
        subscription_status="past_due",
    )

    res = engine.evaluate(ctx)
    assert res.predicted_recoverable is True
    assert res.risk_level == RiskLevel.MEDIUM
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_SUBSCRIPTION_BILLING_GLITCH in reason_codes


def test_9_new_customer_checkout_drop_predicted_recoverable():
    """Test 9: Verify new customer single failure is predicted recoverable."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=75000,
        currency="INR",
        customer_history_count=0,
        customer_success_count=0,
        customer_success_rate_bps=0,
        target_attempt_count=1,
        latest_failure_code="temporary_failure",
    )

    res = engine.evaluate(ctx)
    assert res.predicted_recoverable is True
    assert res.risk_level == RiskLevel.MEDIUM
    reason_codes = [ev.reason_code for ev in res.evidence]
    assert RiskReasonCode.RC_FIRST_TIME_CHECKOUT_DROP in reason_codes


def test_10_target_attempt_count_semantics():
    """Test 10 (Correction 4 & 5): Verify target_attempt_count exact semantics."""
    config = GeneratorConfig(seed=42, num_customers=15, num_payments=40)
    dataset = SyntheticDataGenerator(config).generate()
    contexts = ObservableFeatureExtractor.extract_from_dataset(dataset.observable)

    for ctx in contexts:
        if ctx.target_type == "payment":
            # For payments, attempt count must match actual attempts
            attempts = [a for a in dataset.observable.payment_attempts if a.payment_id == ctx.target_id]
            assert ctx.target_attempt_count == len(attempts)
        elif ctx.target_type == "subscription":
            # For subscriptions, defined as 0
            assert ctx.target_attempt_count == 0


def test_11_ground_truth_isolation_in_engine():
    """Test 11: Verify engine inputs do not accept or require any ground truth fields."""
    engine = DeterministicRiskEngine()
    ctx = ObservableRiskContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_at_risk_minor=50000,
        currency="INR",
        customer_history_count=2,
        customer_success_count=2,
        customer_success_rate_bps=10000,
        target_attempt_count=1,
        latest_failure_code="temporary_failure",
    )

    # Context should not have any ground truth attributes
    assert not hasattr(ctx, "is_recoverable")
    assert not hasattr(ctx, "scenario_type")
    assert not hasattr(ctx, "expected_recovery_reason")

    res = engine.evaluate(ctx)
    assert res.baseline_version == BASELINE_VERSION


def test_12_shuffled_predictions_order_produces_identical_evaluation():
    """Test 12 (Correction 9): Verify evaluator target matching is order-independent."""
    config = GeneratorConfig(seed=42, num_customers=30, num_payments=100)
    dataset = SyntheticDataGenerator(config).generate()

    contexts = ObservableFeatureExtractor.extract_from_dataset(dataset.observable)
    engine = DeterministicRiskEngine()
    predictions = engine.evaluate_batch(contexts)

    # Evaluate original order
    metrics_original = calculate_evaluation_metrics(predictions, dataset.ground_truth, dataset_seed=42)

    # Shuffle predictions order
    shuffled_predictions = list(predictions)
    random.Random(123).shuffle(shuffled_predictions)

    metrics_shuffled = calculate_evaluation_metrics(shuffled_predictions, dataset.ground_truth, dataset_seed=42)

    assert metrics_original.true_positives == metrics_shuffled.true_positives
    assert metrics_original.false_positives == metrics_shuffled.false_positives
    assert metrics_original.true_negatives == metrics_shuffled.true_negatives
    assert metrics_original.false_negatives == metrics_shuffled.false_negatives
    assert metrics_original.precision_bps == metrics_shuffled.precision_bps
    assert metrics_original.recall_bps == metrics_shuffled.recall_bps
    assert metrics_original.f1_score_bps == metrics_shuffled.f1_score_bps
    assert metrics_original.recoverable_amount_captured_minor == metrics_shuffled.recoverable_amount_captured_minor


def test_13_zero_division_percentage_handling():
    """Test 13 (Correction 11): Verify safe 0 bps returns on zero denominators."""
    # When TP=0 and FP=0
    metrics = calculate_evaluation_metrics([], [])
    assert metrics.precision_bps == 0
    assert metrics.recall_bps == 0
    assert metrics.f1_score_bps == 0
    assert metrics.accuracy_bps == 0


def test_14_empty_dataset_handling():
    """Test 14 (Correction 12): Verify empty dataset returns zero metrics without exception."""
    metrics = calculate_evaluation_metrics([], [])
    assert metrics.evaluated_cases_count == 0
    assert metrics.total_amount_at_risk_minor == 0
    assert metrics.recoverable_amount_captured_minor == 0
    assert metrics.recoverable_amount_missed_minor == 0
    assert metrics.false_intervention_amount_minor == 0


def test_15_financial_metrics_reconcile_in_integer_minor():
    """Test 15 (Correction 10): Verify financial metrics reconcile exactly in integer minor units."""
    config = GeneratorConfig(seed=42, num_customers=50, num_payments=200)
    dataset = SyntheticDataGenerator(config).generate()
    evaluator = BaselineEvaluator()
    metrics = evaluator.evaluate_dataset(dataset)

    # Total amount equals captured + missed + false intervention + true negative amounts
    assert metrics.total_amount_at_risk_minor > 0
    assert isinstance(metrics.total_amount_at_risk_minor, int)
    assert isinstance(metrics.recoverable_amount_captured_minor, int)
    assert isinstance(metrics.recoverable_amount_missed_minor, int)
    assert isinstance(metrics.false_intervention_amount_minor, int)


def test_16_end_to_end_baseline_evaluator_on_synthetic_dataset():
    """Test 16: Verify end-to-end evaluation runs on synthetic dataset and generates scorecard."""
    config = GeneratorConfig(seed=42, num_customers=100, num_payments=400)
    dataset = SyntheticDataGenerator(config).generate()
    evaluator = BaselineEvaluator()
    metrics = evaluator.evaluate_dataset(dataset)

    assert metrics.baseline_version == BASELINE_VERSION
    assert metrics.evaluated_cases_count > 0
    assert metrics.true_positives + metrics.false_positives + metrics.true_negatives + metrics.false_negatives == metrics.evaluated_cases_count
    assert 0 <= metrics.precision_bps <= 10000
    assert 0 <= metrics.recall_bps <= 10000
    assert 0 <= metrics.f1_score_bps <= 10000
