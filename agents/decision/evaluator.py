"""Evaluation harness for Phase 5 Recovery Decision Agent."""

from typing import Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from data.synthetic.models import RecoveryGroundTruth, SyntheticDataset
from agents.decision.policy import DEFAULT_RECOVERY_POLICY, RecoveryPolicy
from agents.decision.schemas import (
    DECISION_VERSION,
    DecisionInputContext,
    DecisionStatus,
    POLICY_VERSION,
    RecoveryActionType,
    RecoveryDecisionProposal,
)
from agents.decision.service import RecoveryDecisionAgent
from agents.diagnosis.context_builder import AIDiagnosisContextBuilder
from agents.diagnosis.providers.mock import MockLLMProvider
from agents.diagnosis.service import DiagnosisAgent
from services.risk_engine.extractor import ObservableFeatureExtractor


class DecisionBenchmarkReport(BaseModel):
    """Benchmark evaluation report for Recovery Decision Agent proposals."""

    decision_version: str = DECISION_VERSION
    policy_version: str = POLICY_VERSION
    dataset_seed: Optional[int] = None
    evaluated_proposals_count: int
    action_type_counts: Dict[str, int] = Field(default_factory=dict)
    decision_status_counts: Dict[str, int] = Field(default_factory=dict)

    # Financial Exposure by Action (in paise)
    total_amount_at_risk_minor: int
    proposed_action_amount_minor: int
    human_review_amount_minor: int
    blocked_action_amount_minor: int
    no_action_amount_minor: int

    # Safety & Escalation Invariants
    human_review_escalation_rate_bps: int
    blocked_rate_bps: int
    unsafe_action_proposal_count: int  # Must strictly be 0


class RecoveryDecisionEvaluator:
    """Evaluates decision proposals against ground truth and verifies safety invariants."""

    @staticmethod
    def evaluate_proposals(
        proposals: List[RecoveryDecisionProposal],
        ground_truth: List[RecoveryGroundTruth],
        dataset_seed: Optional[int] = None,
    ) -> DecisionBenchmarkReport:
        """Evaluate a collection of decision proposals."""
        gt_map: Dict[uuid.UUID, RecoveryGroundTruth] = {gt.case_id: gt for gt in ground_truth}

        total_count = len(proposals)
        action_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}

        total_amount = 0
        proposed_amount = 0
        human_review_amount = 0
        blocked_amount = 0
        no_action_amount = 0

        unsafe_count = 0

        for prop in proposals:
            action_counts[prop.action_type.value] = action_counts.get(prop.action_type.value, 0) + 1
            status_counts[prop.decision_status.value] = status_counts.get(prop.decision_status.value, 0) + 1

            total_amount += prop.amount_minor

            if prop.decision_status == DecisionStatus.PROPOSED:
                proposed_amount += prop.amount_minor
            elif prop.decision_status == DecisionStatus.REQUIRES_REVIEW:
                human_review_amount += prop.amount_minor
            elif prop.decision_status == DecisionStatus.BLOCKED:
                blocked_amount += prop.amount_minor
            elif prop.decision_status == DecisionStatus.NO_ACTION:
                no_action_amount += prop.amount_minor

            # Safety Audit: An action must NEVER be PROPOSED if requires_human_approval is True
            if prop.decision_status == DecisionStatus.PROPOSED and prop.requires_human_approval:
                unsafe_count += 1

        review_count = status_counts.get(DecisionStatus.REQUIRES_REVIEW.value, 0)
        blocked_count = status_counts.get(DecisionStatus.BLOCKED.value, 0)

        review_rate_bps = (review_count * 10000) // total_count if total_count > 0 else 0
        blocked_rate_bps = (blocked_count * 10000) // total_count if total_count > 0 else 0

        first_prop = proposals[0] if proposals else None

        return DecisionBenchmarkReport(
            decision_version=first_prop.decision_version if first_prop else DECISION_VERSION,
            policy_version=first_prop.policy_version if first_prop else POLICY_VERSION,
            dataset_seed=dataset_seed,
            evaluated_proposals_count=total_count,
            action_type_counts=action_counts,
            decision_status_counts=status_counts,
            total_amount_at_risk_minor=total_amount,
            proposed_action_amount_minor=proposed_amount,
            human_review_amount_minor=human_review_amount,
            blocked_action_amount_minor=blocked_amount,
            no_action_amount_minor=no_action_amount,
            human_review_escalation_rate_bps=review_rate_bps,
            blocked_rate_bps=blocked_rate_bps,
            unsafe_action_proposal_count=unsafe_count,
        )

    async def evaluate_dataset(
        self,
        dataset: SyntheticDataset,
        policy: RecoveryPolicy = DEFAULT_RECOVERY_POLICY,
    ) -> DecisionBenchmarkReport:
        """End-to-end diagnosis and recovery decision proposal evaluation."""
        # 1. Extract observable contexts & AI contexts
        obs_contexts = ObservableFeatureExtractor.extract_from_dataset(dataset.observable)
        ai_contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)

        # 2. Run Phase 4 Diagnosis Agent
        diagnosis_agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
        ai_diagnoses = await diagnosis_agent.diagnose_batch(ai_contexts)
        ai_diag_map = {d.case_id: d for d in ai_diagnoses if d.case_id}

        # 3. Assemble DecisionInputContexts
        decision_contexts: List[DecisionInputContext] = []
        for ctx in obs_contexts:
            ai_diag = ai_diag_map.get(ctx.case_id)
            d_ctx = DecisionInputContext(
                case_id=ctx.case_id,
                target_type=ctx.target_type,
                target_id=ctx.target_id,
                customer_id=ctx.customer_id,
                amount_minor=ctx.amount_at_risk_minor,
                currency=ctx.currency,
                amount_display=f"₹{ctx.amount_at_risk_minor / 100:,.2f}",
                customer_history_count=ctx.customer_history_count,
                customer_success_count=ctx.customer_success_count,
                customer_success_rate_bps=ctx.customer_success_rate_bps,
                target_attempt_count=ctx.target_attempt_count,
                latest_failure_code=ctx.latest_failure_code,
                subscription_status=ctx.subscription_status,
                ai_diagnosis=ai_diag,
            )
            decision_contexts.append(d_ctx)

        # 4. Synthesize Decision Proposals
        decision_agent = RecoveryDecisionAgent(policy=policy)
        proposals = decision_agent.evaluate_batch(decision_contexts)

        # 5. Evaluate Proposals against Ground Truth
        return self.evaluate_proposals(
            proposals=proposals,
            ground_truth=dataset.ground_truth,
            dataset_seed=dataset.config.seed,
        )
