"""Integer basis-point and minor-unit evaluation metric calculations."""

from collections import Counter
from typing import Dict, List
import uuid

from data.synthetic.models import RecoveryGroundTruth
from services.risk_engine.models import (
    BASELINE_VERSION,
    EvaluationMetrics,
    RiskEvaluationResult,
)


def calculate_evaluation_metrics(
    predictions: List[RiskEvaluationResult],
    ground_truth: List[RecoveryGroundTruth],
    dataset_seed: int = None,
) -> EvaluationMetrics:
    """Calculate confusion matrix, basis-point metrics, and financial reconciliations.

    All percentage metrics use integer basis points (0-10000 bps) with safe zero-denominator handling.
    All financial amounts use integer minor units (paise).
    """
    if not predictions or not ground_truth:
        return EvaluationMetrics(
            baseline_version=BASELINE_VERSION,
            dataset_seed=dataset_seed,
            evaluated_cases_count=0,
            true_positives=0,
            false_positives=0,
            true_negatives=0,
            false_negatives=0,
            precision_bps=0,
            recall_bps=0,
            f1_score_bps=0,
            accuracy_bps=0,
            total_amount_at_risk_minor=0,
            recoverable_amount_captured_minor=0,
            recoverable_amount_missed_minor=0,
            false_intervention_amount_minor=0,
            revenue_capture_rate_bps=0,
            rule_firing_counts={},
        )

    # Index ground truth by case_id for deterministic order-independent matching
    gt_map: Dict[uuid.UUID, RecoveryGroundTruth] = {gt.case_id: gt for gt in ground_truth}

    tp = 0
    fp = 0
    tn = 0
    fn = 0

    total_amount_at_risk_minor = 0
    recoverable_amount_captured_minor = 0
    recoverable_amount_missed_minor = 0
    false_intervention_amount_minor = 0
    total_recoverable_ground_truth_minor = 0

    rule_counter = Counter()

    for pred in predictions:
        if pred.case_id not in gt_map:
            continue

        gt = gt_map[pred.case_id]
        total_amount_at_risk_minor += pred.amount_at_risk_minor
        if gt.is_recoverable:
            total_recoverable_ground_truth_minor += pred.amount_at_risk_minor

        for ev in pred.evidence:
            rule_counter[ev.reason_code.value] += 1

        if pred.predicted_recoverable and gt.is_recoverable:
            tp += 1
            recoverable_amount_captured_minor += pred.amount_at_risk_minor
        elif pred.predicted_recoverable and not gt.is_recoverable:
            fp += 1
            false_intervention_amount_minor += pred.amount_at_risk_minor
        elif not pred.predicted_recoverable and not gt.is_recoverable:
            tn += 1
        elif not pred.predicted_recoverable and gt.is_recoverable:
            fn += 1
            recoverable_amount_missed_minor += pred.amount_at_risk_minor

    evaluated_count = tp + fp + tn + fn

    # Integer basis points calculations with zero-division protection
    precision_bps = (tp * 10000) // (tp + fp) if (tp + fp) > 0 else 0
    recall_bps = (tp * 10000) // (tp + fn) if (tp + fn) > 0 else 0
    f1_score_bps = (
        (2 * precision_bps * recall_bps) // (precision_bps + recall_bps)
        if (precision_bps + recall_bps) > 0
        else 0
    )
    accuracy_bps = ((tp + tn) * 10000) // evaluated_count if evaluated_count > 0 else 0

    revenue_capture_rate_bps = (
        (recoverable_amount_captured_minor * 10000) // total_recoverable_ground_truth_minor
        if total_recoverable_ground_truth_minor > 0
        else 0
    )

    return EvaluationMetrics(
        baseline_version=BASELINE_VERSION,
        dataset_seed=dataset_seed,
        evaluated_cases_count=evaluated_count,
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision_bps=precision_bps,
        recall_bps=recall_bps,
        f1_score_bps=f1_score_bps,
        accuracy_bps=accuracy_bps,
        total_amount_at_risk_minor=total_amount_at_risk_minor,
        recoverable_amount_captured_minor=recoverable_amount_captured_minor,
        recoverable_amount_missed_minor=recoverable_amount_missed_minor,
        false_intervention_amount_minor=false_intervention_amount_minor,
        revenue_capture_rate_bps=revenue_capture_rate_bps,
        rule_firing_counts=dict(rule_counter),
    )
