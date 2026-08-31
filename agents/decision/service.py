"""Recovery Decision Agent synthesizing structured decision proposals under deterministic policy rules."""

from typing import List
import uuid

from agents.decision.policy import DEFAULT_RECOVERY_POLICY, RecoveryPolicy
from agents.decision.schemas import (
    DECISION_VERSION,
    DecisionInputContext,
    DecisionStatus,
    ExplanationChain,
    RecoveryActionType,
    RecoveryDecisionProposal,
)
from agents.diagnosis.schemas import DiagnosisCategory, DiagnosisStatus


def derive_deterministic_proposal_id(
    decision_version: str,
    policy_version: str,
    target_type: str,
    target_id: uuid.UUID,
) -> uuid.UUID:
    """Deterministically derive proposal UUID from stable input parameters."""
    seed_str = f"recoverai-decision-{decision_version}-{policy_version}-{target_type}-{target_id}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, seed_str)


class RecoveryDecisionAgent:
    """Synthesizes policy-governed recovery action proposals from observable context and AI diagnosis."""

    def __init__(
        self,
        policy: RecoveryPolicy = DEFAULT_RECOVERY_POLICY,
        decision_version: str = DECISION_VERSION,
    ):
        self.policy = policy
        self.decision_version = decision_version

    def evaluate_proposal(self, ctx: DecisionInputContext) -> RecoveryDecisionProposal:
        """Evaluate a single decision context and emit a structured decision proposal."""
        observed_facts: List[str] = [
            f"Target: {ctx.target_type} ({ctx.amount_display})",
            f"History: {ctx.customer_success_count}/{ctx.customer_history_count} payments ({ctx.customer_success_rate_bps} bps)",
            f"Current attempts: {ctx.target_attempt_count}",
        ]
        if ctx.latest_failure_code:
            observed_facts.append(f"Latest decline code: {ctx.latest_failure_code}")
        if ctx.subscription_status:
            observed_facts.append(f"Subscription status: {ctx.subscription_status}")

        ai_inferences: List[str] = []
        if ctx.ai_diagnosis and ctx.ai_diagnosis.status == DiagnosisStatus.SUCCESS:
            ai_inferences.append(f"AI Category: {ctx.ai_diagnosis.diagnosis_category.value}")
            ai_inferences.append(f"AI Assessment: recoverable={ctx.ai_diagnosis.ai_recoverability_assessment}")
            ai_inferences.append(f"AI Confidence: {ctx.ai_diagnosis.confidence.value}")
        elif ctx.ai_diagnosis:
            ai_inferences.append(f"AI Diagnosis Status: {ctx.ai_diagnosis.status.value}")
        else:
            ai_inferences.append("AI Diagnosis: Not Provided")

        policy_checks: List[str] = []
        blocking_conditions: List[str] = []
        cooldown_required = False
        requires_human_approval = False

        # -------------------------------------------------------------
        # 1. DETERMINISTIC SAFETY HARD BLOCKS (PRE بالاترين PRIORITY)
        # -------------------------------------------------------------
        # Invariant 1: Exhausted attempts (>= 3 attempts)
        if ctx.target_attempt_count >= (self.policy.max_retry_attempts + 1):
            policy_checks.append(f"Attempt count ({ctx.target_attempt_count}) >= retry threshold ({self.policy.max_retry_attempts + 1})")
            blocking_conditions.append(f"Hard Block: Attempt limit ({self.policy.max_retry_attempts}) reached. Automatic retries strictly prohibited.")
            action_type = RecoveryActionType.NO_ACTION
            decision_status = DecisionStatus.BLOCKED
            rationale = "Opportunity blocked from recovery due to exhausted consecutive attempt limit."

        # Invariant 2: Chronic failure history with unmitigated decline code
        elif (
            ctx.customer_history_count >= 3
            and ctx.customer_success_rate_bps < 2500
            and ctx.latest_failure_code in self.policy.blocked_decline_codes
        ):
            policy_checks.append(f"Chronic failure history ({ctx.customer_success_rate_bps} bps < 2500 bps) with decline code '{ctx.latest_failure_code}'")
            blocking_conditions.append("Hard Block: Chronic decline history presents unacceptable loss risk.")
            action_type = RecoveryActionType.NO_ACTION
            decision_status = DecisionStatus.BLOCKED
            rationale = "Opportunity blocked from recovery due to chronic issuer decline history."

        # -------------------------------------------------------------
        # 2. HIGH-VALUE ESCALATION (PRE-EMPTIVE HUMAN REVIEW)
        # -------------------------------------------------------------
        elif ctx.amount_minor >= self.policy.high_value_threshold_minor:
            policy_checks.append(f"Amount ({ctx.amount_minor} paise) >= high-value threshold ({self.policy.high_value_threshold_minor} paise)")
            action_type = RecoveryActionType.HUMAN_REVIEW
            decision_status = DecisionStatus.REQUIRES_REVIEW
            requires_human_approval = True
            rationale = f"High-value transaction ({ctx.amount_display}) requires human authorization prior to recovery execution."

        # -------------------------------------------------------------
        # 3. AI FAILURE / UNKNOWN DECLIINE ESCALATION
        # -------------------------------------------------------------
        elif ctx.ai_diagnosis and ctx.ai_diagnosis.status != DiagnosisStatus.SUCCESS:
            policy_checks.append(f"AI diagnosis execution returned {ctx.ai_diagnosis.status.value}; escalating to human review.")
            action_type = RecoveryActionType.HUMAN_REVIEW
            decision_status = DecisionStatus.REQUIRES_REVIEW
            requires_human_approval = True
            blocking_conditions.append(f"AI provider status was {ctx.ai_diagnosis.status.value}")
            rationale = "AI diagnosis unavailable; escalated to operations for review."

        elif ctx.latest_failure_code == "unknown_failure":
            policy_checks.append("Unknown gateway failure code detected; escalating to human review.")
            action_type = RecoveryActionType.HUMAN_REVIEW
            decision_status = DecisionStatus.REQUIRES_REVIEW
            requires_human_approval = True
            rationale = "Unclassified gateway decline code requires human evaluation."

        # -------------------------------------------------------------
        # 4. DETERMINISTIC DOMAIN & FAILURE CATEGORY ROUTING
        # -------------------------------------------------------------
        # Subscription Recovery Workflow
        elif ctx.target_type == "subscription" and ctx.subscription_status == "past_due":
            policy_checks.append("Subscription is marked past_due; eligible for subscription recovery workflow.")
            action_type = RecoveryActionType.SUBSCRIPTION_RECOVERY_WORKFLOW
            decision_status = DecisionStatus.PROPOSED
            rationale = "Recurring billing past_due event routed to subscription recovery workflow."

        # Expired or Invalid Payment Method
        elif (
            ctx.latest_failure_code == "expired_payment_method"
            or (ctx.ai_diagnosis and ctx.ai_diagnosis.diagnosis_category == DiagnosisCategory.EXPIRED_OR_INVALID_METHOD)
        ):
            policy_checks.append("Expired or invalid payment method identified; eligible for customer update link.")
            action_type = RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE
            decision_status = DecisionStatus.PROPOSED
            rationale = "Payment method requires customer update intervention."

        # Insufficient Funds (Candidate for retry later with cooldown)
        elif (
            ctx.latest_failure_code == "insufficient_funds"
            or (ctx.ai_diagnosis and ctx.ai_diagnosis.diagnosis_category == DiagnosisCategory.BALANCE_OR_LIMIT_DEFICIT)
        ):
            policy_checks.append("Insufficient funds on actionable attempt; scheduled retry later eligible with cooldown.")
            action_type = RecoveryActionType.RETRY_LATER
            decision_status = DecisionStatus.PROPOSED
            cooldown_required = True
            rationale = "Balance deficit eligible for scheduled retry after cooldown window."

        # Transient Switch Glitch with Proven Reliability or New Customer
        elif (
            ctx.latest_failure_code == "temporary_failure"
            or (ctx.ai_diagnosis and ctx.ai_diagnosis.diagnosis_category == DiagnosisCategory.TRANSIENT_SYSTEM_ERROR)
        ):
            policy_checks.append("Transient network or switch glitch on actionable attempt; automated retry permitted.")
            action_type = RecoveryActionType.RETRY_PAYMENT
            decision_status = DecisionStatus.PROPOSED
            rationale = "Transient gateway error eligible for immediate payment retry."

        # Persistent Issuer Decline on Unproven Account
        elif (
            ctx.latest_failure_code == "generic_decline"
            or (ctx.ai_diagnosis and ctx.ai_diagnosis.diagnosis_category == DiagnosisCategory.PERSISTENT_ISSUER_DECLINE)
        ):
            policy_checks.append("Persistent issuer decline on unproven account; automated retry blocked.")
            action_type = RecoveryActionType.NO_ACTION
            decision_status = DecisionStatus.BLOCKED
            blocking_conditions.append("Issuer decline without mitigating positive historical signals.")
            rationale = "Hard decline on unproven account blocked from automated retry."

        # Fallback / Unclassified
        else:
            policy_checks.append("No actionable recovery pattern matched.")
            action_type = RecoveryActionType.NO_ACTION
            decision_status = DecisionStatus.NO_ACTION
            blocking_conditions.append("Unclassified decline without actionable recovery signals.")
            rationale = "Opportunity does not warrant automated recovery intervention."

        proposal_id = derive_deterministic_proposal_id(
            decision_version=self.decision_version,
            policy_version=self.policy.policy_version,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
        )

        return RecoveryDecisionProposal(
            decision_version=self.decision_version,
            policy_version=self.policy.policy_version,
            proposal_id=proposal_id,
            case_id=ctx.case_id,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
            amount_minor=ctx.amount_minor,
            currency=ctx.currency,
            amount_display=ctx.amount_display,
            action_type=action_type,
            decision_status=decision_status,
            explanation=ExplanationChain(
                observed_facts=observed_facts,
                ai_inferences=ai_inferences,
                policy_checks=policy_checks,
                final_rationale=rationale,
            ),
            cooldown_required=cooldown_required,
            requires_human_approval=requires_human_approval,
            blocking_conditions=blocking_conditions,
        )

    def evaluate_batch(self, contexts: List[DecisionInputContext]) -> List[RecoveryDecisionProposal]:
        """Evaluate a collection of decision contexts."""
        return [self.evaluate_proposal(ctx) for ctx in contexts]
