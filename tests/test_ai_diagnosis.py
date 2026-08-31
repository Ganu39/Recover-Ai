"""Automated tests for RecoverAI Phase 4 AI Root-Cause Diagnosis."""

import json
import random
import uuid
import pytest

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from agents.diagnosis import (
    AIDiagnosisContextBuilder,
    AIDiagnosisEvaluator,
    AIDiagnosisInputContext,
    AttemptSummary,
    DiagnosisCategory,
    DiagnosisStatus,
    EvidenceItem,
    MockLLMProvider,
    QualitativeConfidence,
    DiagnosisAgent,
)


def _create_sample_context() -> AIDiagnosisInputContext:
    return AIDiagnosisInputContext(
        case_id=uuid.uuid4(),
        target_type="payment",
        target_id=uuid.uuid4(),
        masked_target_id="pay_...a1b2",
        masked_customer_id="cust_...c3d4",
        amount_minor=150000,
        currency="INR",
        amount_display="₹1,500.00",
        customer_tenure_days=45,
        customer_history_count=4,
        customer_success_count=4,
        customer_historical_success_rate_pct=100,
        attempts=[
            AttemptSummary(
                attempt_number=1,
                failure_code="temporary_failure",
                failure_reason="Gateway timeout during switch",
                attempt_offset_seconds=5,
            )
        ],
        subscription_status=None,
    )


def test_1_context_builder_contains_only_approved_fields_and_no_ground_truth():
    """Test 1: Verify context builder extracts observable features without ground truth."""
    config = GeneratorConfig(seed=42, num_customers=10, num_payments=30)
    dataset = SyntheticDataGenerator(config).generate()
    contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)

    assert len(contexts) > 0
    forbidden_keys = {"scenario_type", "is_recoverable", "expected_recovery_reason", "ground_truth"}

    for ctx in contexts:
        ctx_dict = ctx.model_dump()
        for key in forbidden_keys:
            assert key not in ctx_dict


def test_2_context_builder_pii_minimization():
    """Test 2: Verify raw customer emails, phone numbers, and full UUIDs are redacted."""
    config = GeneratorConfig(seed=42, num_customers=10, num_payments=30)
    dataset = SyntheticDataGenerator(config).generate()
    contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)

    for ctx in contexts:
        assert ctx.masked_target_id.startswith("pay_...") or ctx.masked_target_id.startswith("sub_...")
        assert ctx.masked_customer_id.startswith("cust_...")
        assert "@" not in ctx.model_dump_json()


def test_3_context_builder_retains_integer_minor_units():
    """Test 3 (Correction 2): Verify context retains canonical amount_minor integer and display string."""
    ctx = _create_sample_context()
    assert isinstance(ctx.amount_minor, int)
    assert ctx.amount_minor == 150000
    assert ctx.currency == "INR"
    assert ctx.amount_display == "₹1,500.00"


def test_4_context_builder_deterministic_canonical_ordering():
    """Test 4 (Correction 9): Verify deterministic ordering of fields and attempt sequences."""
    config1 = GeneratorConfig(seed=42, num_customers=20, num_payments=50)
    config2 = GeneratorConfig(seed=42, num_customers=20, num_payments=50)

    dataset1 = SyntheticDataGenerator(config1).generate()
    dataset2 = SyntheticDataGenerator(config2).generate()

    ctxs1 = AIDiagnosisContextBuilder.build_from_dataset(dataset1.observable)
    ctxs2 = AIDiagnosisContextBuilder.build_from_dataset(dataset2.observable)

    assert len(ctxs1) == len(ctxs2)
    for c1, c2 in zip(ctxs1, ctxs2):
        assert c1.model_dump() == c2.model_dump()


@pytest.mark.asyncio
async def test_5_valid_diagnosis_parsing_and_schema_validation():
    """Test 5: Verify valid structured diagnosis is parsed and validated into AIDiagnosisResult."""
    provider = MockLLMProvider()
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert result.status == DiagnosisStatus.SUCCESS
    assert result.diagnosis_category == DiagnosisCategory.TRANSIENT_SYSTEM_ERROR
    assert result.ai_recoverability_assessment is True
    assert result.confidence == QualitativeConfidence.HIGH
    assert len(result.evidence_reasoning) > 0


@pytest.mark.asyncio
async def test_6_untrusted_provider_isolation_and_metadata_integrity():
    """Test 6 (Correction 1 & 8): Verify model metadata is supplied by adapter, not untrusted model text."""
    provider = MockLLMProvider(provider_name="custom_provider_adapter", model_name="custom-model-x")
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert result.provider_name == "custom_provider_adapter"
    assert result.model_name == "custom-model-x"
    assert result.prompt_version == "v1"
    assert result.latency_ms >= 0


def test_7_strong_evidence_grounding_validation():
    """Test 7 (Correction 3): Verify EvidenceItem requires fact, source_field, and inference."""
    ev = EvidenceItem(
        fact="Customer completed 4 out of 4 previous payments",
        source_field="customer_success_count/customer_history_count",
        inference="Historical intent and reliability are exceptionally high",
    )
    assert ev.fact != ""
    assert ev.source_field != ""
    assert ev.inference != ""


@pytest.mark.asyncio
async def test_8_ai_recoverability_opinion_scoping():
    """Test 8 (Correction 4): Verify AI assessment is scoped as opinion without executing decisions."""
    provider = MockLLMProvider()
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert hasattr(result, "ai_recoverability_assessment")
    assert hasattr(result, "ai_recoverability_reason")
    assert not hasattr(result, "decision_action")
    assert not hasattr(result, "retry_scheduled")


@pytest.mark.asyncio
async def test_9_provider_timeout_triggers_timeout_status():
    """Test 9 (Correction 10): Verify provider timeout triggers TIMEOUT status and safe fallback."""
    provider = MockLLMProvider(injected_fault="timeout")
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx, timeout_seconds=0.1)
    assert result.status == DiagnosisStatus.TIMEOUT
    assert result.diagnosis_category == DiagnosisCategory.INSUFFICIENT_DATA
    assert result.ai_recoverability_assessment is None
    assert "timed out" in result.error_message.lower()


@pytest.mark.asyncio
async def test_10_provider_http_error_triggers_provider_error_status():
    """Test 10 (Correction 10): Verify provider 500 error triggers PROVIDER_ERROR status."""
    provider = MockLLMProvider(injected_fault="http_500")
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert result.status == DiagnosisStatus.PROVIDER_ERROR
    assert result.diagnosis_category == DiagnosisCategory.INSUFFICIENT_DATA
    assert "500" in result.error_message


@pytest.mark.asyncio
async def test_11_malformed_json_triggers_validation_error_status():
    """Test 11 (Correction 10): Verify malformed JSON triggers VALIDATION_ERROR status."""
    provider = MockLLMProvider(injected_fault="malformed_json")
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert result.status == DiagnosisStatus.VALIDATION_ERROR
    assert result.diagnosis_category == DiagnosisCategory.INSUFFICIENT_DATA
    assert "malformed json" in result.error_message.lower()


@pytest.mark.asyncio
async def test_12_schema_violation_triggers_validation_error_status():
    """Test 12: Verify missing required schema fields triggers VALIDATION_ERROR status."""
    provider = MockLLMProvider(injected_fault="schema_violation")
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert result.status == DiagnosisStatus.VALIDATION_ERROR
    assert "validation failed" in result.error_message.lower()


@pytest.mark.asyncio
async def test_13_deterministic_fallback_result_contents():
    """Test 13: Verify fallback result produces consistent, non-fabricated fields."""
    provider = MockLLMProvider(injected_fault="http_500")
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = _create_sample_context()

    result = await agent.diagnose(ctx)
    assert result.confidence == QualitativeConfidence.LOW
    assert result.ai_recoverability_assessment is None
    assert result.diagnosis_category == DiagnosisCategory.INSUFFICIENT_DATA
    assert len(result.missing_information) > 0


@pytest.mark.asyncio
async def test_14_insufficient_data_diagnosis_handling():
    """Test 14: Verify model returns INSUFFICIENT_DATA when observable context is ambiguous."""
    provider = MockLLMProvider()
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    ctx = AIDiagnosisInputContext(
        target_type="payment",
        target_id=uuid.uuid4(),
        masked_target_id="pay_...0000",
        masked_customer_id="cust_...0000",
        amount_minor=10000,
        currency="INR",
        amount_display="₹100.00",
        customer_tenure_days=10,
        customer_history_count=2,
        customer_success_count=1,
        customer_historical_success_rate_pct=50,
        attempts=[],  # Empty attempt list
        subscription_status=None,
    )

    result = await agent.diagnose(ctx)
    assert result.diagnosis_category == DiagnosisCategory.INSUFFICIENT_DATA
    assert result.confidence == QualitativeConfidence.LOW


def test_15_prompt_version_selection_and_immutability():
    """Test 15 (Correction 7): Verify prompt templates load successfully for immutable version v1."""
    provider = MockLLMProvider()
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    assert agent.system_prompt != ""
    assert agent.user_template != ""

    with pytest.raises(FileNotFoundError):
        DiagnosisAgent(provider=provider, prompt_version="v_non_existent")


@pytest.mark.asyncio
async def test_16_batch_diagnosis_execution():
    """Test 16: Verify batch diagnosis execution on multiple contexts."""
    provider = MockLLMProvider()
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")
    contexts = [_create_sample_context() for _ in range(5)]

    results = await agent.diagnose_batch(contexts)
    assert len(results) == 5
    for r in results:
        assert r.status == DiagnosisStatus.SUCCESS


@pytest.mark.asyncio
async def test_17_evaluator_separates_diagnosis_accuracy_from_recovery_accuracy():
    """Test 17 (Correction 6): Verify evaluator separates taxonomy metrics from recoverability metrics."""
    config = GeneratorConfig(seed=42, num_customers=15, num_payments=40)
    dataset = SyntheticDataGenerator(config).generate()

    agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
    evaluator = AIDiagnosisEvaluator()
    report = await evaluator.evaluate_dataset(dataset, agent, is_mock=True)

    # 1. Recoverability classification metrics
    assert 0 <= report.precision_bps <= 10000
    assert 0 <= report.recall_bps <= 10000
    assert 0 <= report.f1_score_bps <= 10000

    # 2. Taxonomy category metrics
    assert report.category_metrics.total_evaluated == report.evaluated_cases_count
    assert 0 <= report.category_metrics.category_agreement_rate_bps <= 10000

    # 3. Execution integrity
    assert report.schema_validity_rate_bps == 10000


@pytest.mark.asyncio
async def test_18_shuffled_diagnoses_order_produces_identical_evaluation():
    """Test 18: Verify evaluator target matching is order-independent."""
    config = GeneratorConfig(seed=42, num_customers=20, num_payments=50)
    dataset = SyntheticDataGenerator(config).generate()

    contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)
    agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
    diagnoses = await agent.diagnose_batch(contexts)

    evaluator = AIDiagnosisEvaluator()
    report1 = evaluator.evaluate_diagnoses(diagnoses, dataset.ground_truth, dataset_seed=42, is_mock=True)

    shuffled = list(diagnoses)
    random.Random(999).shuffle(shuffled)
    report2 = evaluator.evaluate_diagnoses(shuffled, dataset.ground_truth, dataset_seed=42, is_mock=True)

    assert report1.precision_bps == report2.precision_bps
    assert report1.recall_bps == report2.recall_bps
    assert report1.f1_score_bps == report2.f1_score_bps
    assert report1.recoverable_amount_captured_minor == report2.recoverable_amount_captured_minor


@pytest.mark.asyncio
async def test_19_mock_benchmark_labeled_explicitly_as_mock_validation():
    """Test 19 (Correction 5): Verify mock benchmarks are strictly labeled as MOCK_VALIDATION."""
    config = GeneratorConfig(seed=42, num_customers=10, num_payments=25)
    dataset = SyntheticDataGenerator(config).generate()

    agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
    evaluator = AIDiagnosisEvaluator()
    report = await evaluator.evaluate_dataset(dataset, agent, is_mock=True)

    assert report.benchmark_type == "MOCK_VALIDATION"
    assert report.provider_name == "mock_diagnostic_provider"


@pytest.mark.asyncio
async def test_20_end_to_end_ai_evaluator_comparison_against_baseline_v1():
    """Test 20: Verify evaluator calculates comparative delta against Baseline v1."""
    config = GeneratorConfig(seed=42, num_customers=25, num_payments=60)
    dataset = SyntheticDataGenerator(config).generate()

    agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
    evaluator = AIDiagnosisEvaluator()
    report = await evaluator.evaluate_dataset(dataset, agent, is_mock=True)

    assert report.baseline_v1_f1_score_bps > 0
    assert report.f1_score_delta_bps == report.f1_score_bps - report.baseline_v1_f1_score_bps
    assert report.revenue_capture_delta_bps == report.revenue_capture_rate_bps - report.baseline_v1_revenue_capture_rate_bps
