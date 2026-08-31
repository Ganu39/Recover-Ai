"""Deterministic Revenue-Risk Engine executing Baseline Version v1."""

from typing import List
from services.risk_engine.models import (
    BASELINE_VERSION,
    ObservableRiskContext,
    RiskEvaluationResult,
)
from services.risk_engine.rules import evaluate_rules_v1


class DeterministicRiskEngine:
    """Non-AI deterministic revenue-risk evaluation engine."""

    def __init__(self, version: str = BASELINE_VERSION):
        self.version = version

    def evaluate(self, ctx: ObservableRiskContext) -> RiskEvaluationResult:
        """Evaluate a single observable transaction context."""
        predicted_recoverable, risk_level, evidence = evaluate_rules_v1(ctx)

        return RiskEvaluationResult(
            baseline_version=self.version,
            case_id=ctx.case_id,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
            predicted_recoverable=predicted_recoverable,
            risk_level=risk_level,
            amount_at_risk_minor=ctx.amount_at_risk_minor,
            currency=ctx.currency,
            evidence=evidence,
        )

    def evaluate_batch(self, contexts: List[ObservableRiskContext]) -> List[RiskEvaluationResult]:
        """Evaluate a collection of observable contexts in batch."""
        return [self.evaluate(ctx) for ctx in contexts]
