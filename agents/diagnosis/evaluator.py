"""Evaluation harness for AI Root-Cause Diagnosis separating accuracy dimensions and comparing against Baseline v1."""

from typing import Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from data.synthetic.models import RecoveryGroundTruth, ScenarioType, SyntheticDataset
from agents.diagnosis.context_builder import AIDiagnosisContextBuilder
from agents.diagnosis.schemas import (
    AIDiagnosisResult,
    DiagnosisCategory,
    DiagnosisStatus,
)
from agents.diagnosis.service import DiagnosisAgent
from services.risk_engine.evaluator import BaselineEvaluator
from services.risk_engine.models import EvaluationMetrics


class DiagnosisCategoryMetrics(BaseModel):
    """Multi-class evaluation metrics for diagnosis taxonomy classification."""

    total_evaluated: int
    category_counts: Dict[str, int] = Field(default_factory=dict)
    ground_truth_scenario_agreement_count: int
    category_agreement_rate_bps: int  # Agreement in bps


class AIBenchmarkReport(BaseModel):
    """Comprehensive benchmark evaluation report for Phase 4 AI Diagnosis."""

    benchmark_type: str  # "MOCK_VALIDATION" or "LIVE_AI"
    prompt_version: str
    provider_name: str
    model_name: str
    dataset_seed: Optional[int]
    evaluated_cases_count: int
    successful_executions: int
    failed_executions: int
    schema_validity_rate_bps: int
    evidence_grounding_rate_bps: int

    # Recoverability Classification Performance
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision_bps: int
    recall_bps: int
    f1_score_bps: int
    accuracy_bps: int

    # Financial Exposure & Revenue Capture
    total_amount_at_risk_minor: int
    recoverable_amount_captured_minor: int
    recoverable_amount_missed_minor: int
    false_intervention_amount_minor: int
    revenue_capture_rate_bps: int

    # Taxonomy Performance
    category_metrics: DiagnosisCategoryMetrics

    # Comparative Baseline Delta
    baseline_v1_f1_score_bps: int
    f1_score_delta_bps: int  # AI F1 - Baseline F1
    baseline_v1_revenue_capture_rate_bps: int
    revenue_capture_delta_bps: int  # AI Capture - Baseline Capture


class AIDiagnosisEvaluator:
    """Evaluates AI diagnosis results against hidden ground truth and compares against Baseline v1."""

    @staticmethod
    def evaluate_diagnoses(
        diagnoses: List[AIDiagnosisResult],
        ground_truth: List[RecoveryGroundTruth],
        dataset_seed: Optional[int] = None,
        baseline_metrics: Optional[EvaluationMetrics] = None,
        is_mock: bool = False,
    ) -> AIBenchmarkReport:
        """Evaluate a set of AI diagnosis results against ground truth."""
        gt_map: Dict[uuid.UUID, RecoveryGroundTruth] = {gt.case_id: gt for gt in ground_truth}

        total_cases = len(diagnoses)
        successful = 0
        failed = 0
        grounded_cases = 0

        tp = 0
        fp = 0
        tn = 0
        fn = 0

        total_amount_at_risk = 0
        captured_amount = 0
        missed_amount = 0
        false_intervention_amount = 0
        total_recoverable_ground_truth_minor = 0

        category_counts = {}
        scenario_agreement_count = 0

        for diag in diagnoses:
            if diag.case_id not in gt_map:
                continue

            gt = gt_map[diag.case_id]
            total_amount_at_risk += diag.amount_minor
            if gt.is_recoverable:
                total_recoverable_ground_truth_minor += diag.amount_minor

            category_counts[diag.diagnosis_category.value] = category_counts.get(diag.diagnosis_category.value, 0) + 1

            if diag.status == DiagnosisStatus.SUCCESS:
                successful += 1
                if diag.evidence_reasoning and all(e.source_field for e in diag.evidence_reasoning):
                    grounded_cases += 1
            else:
                failed += 1

            # Check scenario taxonomy correlation
            if (
                (gt.scenario_type == ScenarioType.SUBSCRIPTION_FAILURE and diag.diagnosis_category == DiagnosisCategory.SUBSCRIPTION_BILLING_ISSUE)
                or (gt.scenario_type == ScenarioType.REPEATED_FAILURE and diag.diagnosis_category == DiagnosisCategory.PERSISTENT_ISSUER_DECLINE)
                or (gt.scenario_type in (ScenarioType.HIGH_PROBABILITY_RECOVERABLE, ScenarioType.TEMPORARY_FAILURE_AFTER_SUCCESS_HISTORY) and diag.diagnosis_category == DiagnosisCategory.TRANSIENT_SYSTEM_ERROR)
                or (gt.scenario_type == ScenarioType.NEW_CUSTOMER and diag.diagnosis_category == DiagnosisCategory.FIRST_TIME_USER_DROP)
                or (gt.scenario_type == ScenarioType.LOW_PROBABILITY_RECOVERABLE and diag.diagnosis_category == DiagnosisCategory.BALANCE_OR_LIMIT_DEFICIT)
            ):
                scenario_agreement_count += 1

            # Evaluate recoverability assessment only for successful diagnoses
            if diag.ai_recoverability_assessment is not None:
                if diag.ai_recoverability_assessment and gt.is_recoverable:
                    tp += 1
                    captured_amount += diag.amount_minor
                elif diag.ai_recoverability_assessment and not gt.is_recoverable:
                    fp += 1
                    false_intervention_amount += diag.amount_minor
                elif not diag.ai_recoverability_assessment and not gt.is_recoverable:
                    tn += 1
                elif not diag.ai_recoverability_assessment and gt.is_recoverable:
                    fn += 1
                    missed_amount += diag.amount_minor

        valid_count = tp + fp + tn + fn
        precision_bps = (tp * 10000) // (tp + fp) if (tp + fp) > 0 else 0
        recall_bps = (tp * 10000) // (tp + fn) if (tp + fn) > 0 else 0
        f1_score_bps = (
            (2 * precision_bps * recall_bps) // (precision_bps + recall_bps)
            if (precision_bps + recall_bps) > 0
            else 0
        )
        accuracy_bps = ((tp + tn) * 10000) // valid_count if valid_count > 0 else 0

        revenue_capture_rate_bps = (
            (captured_amount * 10000) // total_recoverable_ground_truth_minor
            if total_recoverable_ground_truth_minor > 0
            else 0
        )
        schema_validity_rate_bps = (successful * 10000) // total_cases if total_cases > 0 else 0
        evidence_grounding_rate_bps = (grounded_cases * 10000) // successful if successful > 0 else 0
        category_agreement_rate_bps = (scenario_agreement_count * 10000) // total_cases if total_cases > 0 else 0

        # Baseline comparison
        base_f1 = baseline_metrics.f1_score_bps if baseline_metrics else 0
        base_capture = baseline_metrics.revenue_capture_rate_bps if baseline_metrics else 0

        first_diag = diagnoses[0] if diagnoses else None

        return AIBenchmarkReport(
            benchmark_type="MOCK_VALIDATION" if is_mock else "LIVE_AI",
            prompt_version=first_diag.prompt_version if first_diag else "v1",
            provider_name=first_diag.provider_name if first_diag else "unknown",
            model_name=first_diag.model_name if first_diag else "unknown",
            dataset_seed=dataset_seed,
            evaluated_cases_count=total_cases,
            successful_executions=successful,
            failed_executions=failed,
            schema_validity_rate_bps=schema_validity_rate_bps,
            evidence_grounding_rate_bps=evidence_grounding_rate_bps,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision_bps=precision_bps,
            recall_bps=recall_bps,
            f1_score_bps=f1_score_bps,
            accuracy_bps=accuracy_bps,
            total_amount_at_risk_minor=total_amount_at_risk,
            recoverable_amount_captured_minor=captured_amount,
            recoverable_amount_missed_minor=missed_amount,
            false_intervention_amount_minor=false_intervention_amount,
            revenue_capture_rate_bps=revenue_capture_rate_bps,
            category_metrics=DiagnosisCategoryMetrics(
                total_evaluated=total_cases,
                category_counts=category_counts,
                ground_truth_scenario_agreement_count=scenario_agreement_count,
                category_agreement_rate_bps=category_agreement_rate_bps,
            ),
            baseline_v1_f1_score_bps=base_f1,
            f1_score_delta_bps=f1_score_bps - base_f1,
            baseline_v1_revenue_capture_rate_bps=base_capture,
            revenue_capture_delta_bps=revenue_capture_rate_bps - base_capture,
        )

    async def evaluate_dataset(
        self,
        dataset: SyntheticDataset,
        agent: DiagnosisAgent,
        is_mock: bool = False,
    ) -> AIBenchmarkReport:
        """End-to-end diagnosis and evaluation on a SyntheticDataset."""
        # 1. Build sanitized AI contexts (air-gapped)
        contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)

        # 2. Run AI diagnosis batch
        diagnoses = await agent.diagnose_batch(contexts)

        # 3. Calculate baseline metrics for direct side-by-side comparison
        baseline_evaluator = BaselineEvaluator()
        base_metrics = baseline_evaluator.evaluate_dataset(dataset)

        # 4. Compare AI results against ground truth and baseline v1
        return self.evaluate_diagnoses(
            diagnoses=diagnoses,
            ground_truth=dataset.ground_truth,
            dataset_seed=dataset.config.seed,
            baseline_metrics=base_metrics,
            is_mock=is_mock,
        )
