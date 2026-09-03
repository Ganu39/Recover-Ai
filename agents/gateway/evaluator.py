"""Evaluation harness and benchmark calculation for Safety Gateway v1 (Phase 6)."""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from agents.decision.schemas import RecoveryDecisionProposal
from agents.gateway.policy import DEFAULT_GATEWAY_POLICY, GatewayPolicy
from agents.gateway.schemas import (
    DECISION_VERSION,
    GATEWAY_VERSION,
    POLICY_VERSION,
    GatewayDecision,
    GatewayDecisionResult,
    GatewayReasonCode,
    GatewayTargetContext,
    HumanApprovalRecord,
)
from agents.gateway.service import DeterministicSafetyGateway


class GatewayEvaluationReport(BaseModel):
    """Structured evaluation report and benchmark scorecard for Gateway v1."""

    gateway_version: str = GATEWAY_VERSION
    policy_version: str = POLICY_VERSION
    decision_version: str = DECISION_VERSION
    total_evaluated: int = 0
    approved_count: int = 0
    blocked_count: int = 0
    requires_review_count: int = 0
    rate_limited_count: int = 0
    kill_switch_count: int = 0
    invalid_proposal_count: int = 0
    replay_count: int = 0
    unsafe_authorizations: int = 0
    unsafe_authorization_rate_bps: int = 0
    financial_integrity_violations: int = 0
    decision_distribution_bps: Dict[str, int] = Field(default_factory=dict)
    reason_code_counts: Dict[str, int] = Field(default_factory=dict)
    financial_metrics_paise: Dict[str, int] = Field(default_factory=dict)


class GatewayEvaluator:
    """Evaluates the safety gateway across a collection of proposals and trusted target contexts."""

    def __init__(
        self,
        gateway: Optional[DeterministicSafetyGateway] = None,
        policy: Optional[GatewayPolicy] = None,
    ):
        self.gateway = gateway or DeterministicSafetyGateway()
        self.policy = policy or DEFAULT_GATEWAY_POLICY

    def evaluate(
        self,
        triplets: List[Tuple[RecoveryDecisionProposal, GatewayTargetContext, Optional[HumanApprovalRecord]]],
    ) -> Tuple[List[GatewayDecisionResult], GatewayEvaluationReport]:
        """Run evaluation pipeline across triplets and compute metrics."""
        results: List[GatewayDecisionResult] = []

        total_evaluated = len(triplets)
        approved_count = 0
        blocked_count = 0
        requires_review_count = 0
        rate_limited_count = 0
        kill_switch_count = 0
        invalid_proposal_count = 0
        replay_count = 0
        unsafe_authorizations = 0
        financial_integrity_violations = 0

        reason_code_counts: Dict[str, int] = {}
        total_amount_minor = 0
        approved_amount_minor = 0
        blocked_amount_minor = 0
        requires_review_amount_minor = 0

        for proposal, target, approval in triplets:
            res = self.gateway.evaluate_proposal(proposal, target, approval)
            results.append(res)

            code_name = res.reason_code.value
            reason_code_counts[code_name] = reason_code_counts.get(code_name, 0) + 1

            total_amount_minor += target.amount_minor

            if res.is_replay:
                replay_count += 1

            if res.gateway_decision == GatewayDecision.APPROVED:
                approved_count += 1
                approved_amount_minor += target.amount_minor

                # INDEPENDENT AUDIT: Verify that NO unsafe conditions were authorized
                # 1. Attempt cap violation
                if target.target_attempt_count >= (self.policy.max_target_attempts + 1):
                    unsafe_authorizations += 1
                # 2. Chronic decline violation
                if (
                    target.customer_history_count >= 3
                    and target.customer_success_rate_bps < 2500
                    and target.latest_failure_code in self.policy.blocked_decline_codes
                ):
                    unsafe_authorizations += 1
                # 3. High-value without approval
                if target.amount_minor >= self.gateway.config.high_value_threshold_minor:
                    if approval is None or not approval.approval_status:
                        unsafe_authorizations += 1
                # 4. Financial mismatch
                if proposal.amount_minor != target.amount_minor or proposal.currency != target.currency:
                    unsafe_authorizations += 1
                    financial_integrity_violations += 1

            elif res.gateway_decision == GatewayDecision.BLOCKED:
                blocked_count += 1
                blocked_amount_minor += target.amount_minor
            elif res.gateway_decision == GatewayDecision.REQUIRES_REVIEW:
                requires_review_count += 1
                requires_review_amount_minor += target.amount_minor
            elif res.gateway_decision == GatewayDecision.RATE_LIMITED:
                rate_limited_count += 1
            elif res.gateway_decision == GatewayDecision.KILL_SWITCH_ACTIVE:
                kill_switch_count += 1
            elif res.gateway_decision == GatewayDecision.INVALID_PROPOSAL:
                invalid_proposal_count += 1
                if res.reason_code in {
                    GatewayReasonCode.BLOCK_AMOUNT_MISMATCH,
                    GatewayReasonCode.BLOCK_CURRENCY_MISMATCH,
                    GatewayReasonCode.BLOCK_INVALID_FINANCIAL_UNIT,
                }:
                    financial_integrity_violations += 1

        unsafe_rate_bps = (
            (unsafe_authorizations * 10000) // approved_count
            if approved_count > 0
            else 0
        )

        decision_dist_bps = {
            GatewayDecision.APPROVED.value: (approved_count * 10000) // total_evaluated if total_evaluated > 0 else 0,
            GatewayDecision.BLOCKED.value: (blocked_count * 10000) // total_evaluated if total_evaluated > 0 else 0,
            GatewayDecision.REQUIRES_REVIEW.value: (requires_review_count * 10000) // total_evaluated if total_evaluated > 0 else 0,
            GatewayDecision.RATE_LIMITED.value: (rate_limited_count * 10000) // total_evaluated if total_evaluated > 0 else 0,
            GatewayDecision.KILL_SWITCH_ACTIVE.value: (kill_switch_count * 10000) // total_evaluated if total_evaluated > 0 else 0,
            GatewayDecision.INVALID_PROPOSAL.value: (invalid_proposal_count * 10000) // total_evaluated if total_evaluated > 0 else 0,
        }

        report = GatewayEvaluationReport(
            gateway_version=self.gateway.config.gateway_version,
            policy_version=self.gateway.config.policy_version,
            decision_version=self.gateway.config.decision_version,
            total_evaluated=total_evaluated,
            approved_count=approved_count,
            blocked_count=blocked_count,
            requires_review_count=requires_review_count,
            rate_limited_count=rate_limited_count,
            kill_switch_count=kill_switch_count,
            invalid_proposal_count=invalid_proposal_count,
            replay_count=replay_count,
            unsafe_authorizations=unsafe_authorizations,
            unsafe_authorization_rate_bps=unsafe_rate_bps,
            financial_integrity_violations=financial_integrity_violations,
            decision_distribution_bps=decision_dist_bps,
            reason_code_counts=reason_code_counts,
            financial_metrics_paise={
                "total_evaluated_paise": total_amount_minor,
                "approved_paise": approved_amount_minor,
                "blocked_paise": blocked_amount_minor,
                "requires_review_paise": requires_review_amount_minor,
            },
        )
        return results, report
