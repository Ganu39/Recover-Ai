"""Baseline evaluation pipeline comparing risk engine predictions against ground truth."""

from typing import List

from data.synthetic.models import RecoveryGroundTruth, SyntheticDataset
from services.risk_engine.engine import DeterministicRiskEngine
from services.risk_engine.extractor import ObservableFeatureExtractor
from services.risk_engine.metrics import calculate_evaluation_metrics
from services.risk_engine.models import (
    BASELINE_VERSION,
    EvaluationMetrics,
    RiskEvaluationResult,
)


class BaselineEvaluator:
    """Evaluation harness comparing deterministic baseline predictions against air-gapped ground truth."""

    def __init__(self, version: str = BASELINE_VERSION):
        self.version = version
        self.engine = DeterministicRiskEngine(version=version)

    def evaluate_predictions(
        self,
        predictions: List[RiskEvaluationResult],
        ground_truth: List[RecoveryGroundTruth],
        dataset_seed: int = None,
    ) -> EvaluationMetrics:
        """Evaluate a pre-generated set of predictions against ground truth records."""
        return calculate_evaluation_metrics(predictions, ground_truth, dataset_seed=dataset_seed)

    def evaluate_dataset(self, dataset: SyntheticDataset) -> EvaluationMetrics:
        """End-to-end evaluation of a complete SyntheticDataset."""
        # 1. Feature extraction from observable entities only
        contexts = ObservableFeatureExtractor.extract_from_dataset(dataset.observable)

        # 2. Risk engine evaluation (Air-gapped)
        predictions = self.engine.evaluate_batch(contexts)

        # 3. Ground truth comparison
        return self.evaluate_predictions(
            predictions=predictions,
            ground_truth=dataset.ground_truth,
            dataset_seed=dataset.config.seed,
        )
