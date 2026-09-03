"""Deterministic safety check functions for Gateway v1 (Phase 6)."""

from typing import List, Optional, Tuple
import uuid

from agents.decision.schemas import RecoveryActionType, RecoveryDecisionProposal
from agents.gateway.policy import (
    DEFAULT_GATEWAY_POLICY,
    EXECUTABLE_ACTION_ALLOWLIST,
    NON_EXECUTABLE_ACTIONS,
    GatewayPolicy,
)
from agents.gateway.schemas import (
    DECISION_VERSION,
    GATEWAY_VERSION,
    POLICY_VERSION,
    GatewayConfig,
    GatewayDecision,
    GatewayReasonCode,
    GatewayTargetContext,
    HumanApprovalRecord,
)


def derive_expected_proposal_id(
    decision_version: str,
    policy_version: str,
    target_type: str,
    target_id: uuid.UUID,
) -> uuid.UUID:
    """Exact Phase 5 deterministic proposal UUID formula."""
    seed_str = f"recoverai-decision-{decision_version}-{policy_version}-{target_type}-{target_id}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, seed_str)


def check_schema_and_version(
    proposal: RecoveryDecisionProposal,
    target: GatewayTargetContext,
    config: GatewayConfig,
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 1: Validate contract schema and version alignment."""
    if proposal.decision_version != DECISION_VERSION:
        return (
            False,
            GatewayReasonCode.BLOCK_SCHEMA_VALIDATION_FAILED,
            f"Decision version mismatch: expected '{DECISION_VERSION}', received '{proposal.decision_version}'",
        )

    if proposal.policy_version != POLICY_VERSION or config.policy_version != POLICY_VERSION:
        return (
            False,
            GatewayReasonCode.BLOCK_SCHEMA_VALIDATION_FAILED,
            f"Policy version mismatch: expected '{POLICY_VERSION}', received '{proposal.policy_version}'",
        )

    if config.gateway_version != GATEWAY_VERSION:
        return (
            False,
            GatewayReasonCode.GATEWAY_CONFIGURATION_ERROR,
            f"Gateway version mismatch: expected '{GATEWAY_VERSION}', received '{config.gateway_version}'",
        )

    if target.target_type not in {"payment", "subscription"}:
        return (
            False,
            GatewayReasonCode.BLOCK_SCHEMA_VALIDATION_FAILED,
            f"Invalid target_type: '{target.target_type}'. Must be 'payment' or 'subscription'",
        )

    return True, None, "Schema and version contracts validated"


def check_proposal_identity(
    proposal: RecoveryDecisionProposal,
    target: GatewayTargetContext,
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 2: Independently compute and verify deterministic proposal identity."""
    if proposal.target_id != target.target_id:
        return (
            False,
            GatewayReasonCode.BLOCK_PROPOSAL_IDENTITY_MISMATCH,
            f"Target ID mismatch: proposal references {proposal.target_id}, trusted context has {target.target_id}",
        )

    if proposal.target_type != target.target_type:
        return (
            False,
            GatewayReasonCode.BLOCK_PROPOSAL_IDENTITY_MISMATCH,
            f"Target type mismatch: proposal specifies {proposal.target_type}, trusted context has {target.target_type}",
        )

    expected_id = derive_expected_proposal_id(
        decision_version=proposal.decision_version,
        policy_version=proposal.policy_version,
        target_type=proposal.target_type,
        target_id=proposal.target_id,
    )

    if proposal.proposal_id != expected_id:
        return (
            False,
            GatewayReasonCode.BLOCK_PROPOSAL_IDENTITY_MISMATCH,
            f"Proposal ID {proposal.proposal_id} does not match deterministic expectation {expected_id}",
        )

    return True, None, "Proposal identity verified deterministically"


def check_financial_integrity(
    proposal: RecoveryDecisionProposal,
    target: GatewayTargetContext,
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 3: Verify strict integer minor unit amount and currency consistency."""
    # Strict integer type assertion: reject float or non-integer
    if not isinstance(proposal.amount_minor, int) or isinstance(proposal.amount_minor, bool):
        return (
            False,
            GatewayReasonCode.BLOCK_INVALID_FINANCIAL_UNIT,
            "Proposal amount_minor must be an integer paise value",
        )

    if not isinstance(target.amount_minor, int) or isinstance(target.amount_minor, bool):
        return (
            False,
            GatewayReasonCode.BLOCK_INVALID_FINANCIAL_UNIT,
            "Trusted target amount_minor must be an integer paise value",
        )

    if target.amount_minor <= 0 or proposal.amount_minor <= 0:
        return (
            False,
            GatewayReasonCode.BLOCK_INVALID_FINANCIAL_UNIT,
            f"Financial amounts must be strictly positive (> 0 paise). Received: {proposal.amount_minor}",
        )

    if proposal.amount_minor != target.amount_minor:
        return (
            False,
            GatewayReasonCode.BLOCK_AMOUNT_MISMATCH,
            f"Amount mismatch: proposal has {proposal.amount_minor} paise, trusted context has {target.amount_minor} paise",
        )

    if proposal.currency != target.currency:
        return (
            False,
            GatewayReasonCode.BLOCK_CURRENCY_MISMATCH,
            f"Currency mismatch: proposal has '{proposal.currency}', trusted context has '{target.currency}'",
        )

    return True, None, "Financial integrity verified (integer minor units identical)"


def check_action_allowlist(
    proposal: RecoveryDecisionProposal,
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 4: Enforce that only executable recovery action types may be authorized."""
    if proposal.action_type not in EXECUTABLE_ACTION_ALLOWLIST:
        if proposal.action_type == RecoveryActionType.NO_ACTION:
            return (
                False,
                GatewayReasonCode.BLOCK_NON_EXECUTABLE_ACTION,
                "Action NO_ACTION cannot be authorized for execution layer",
            )
        elif proposal.action_type == RecoveryActionType.HUMAN_REVIEW:
            return (
                False,
                GatewayReasonCode.MISSING_HUMAN_APPROVAL,
                "Action HUMAN_REVIEW requires operations human authorization before action execution",
            )
        return (
            False,
            GatewayReasonCode.BLOCK_NON_EXECUTABLE_ACTION,
            f"Action '{proposal.action_type}' is not in the executable allowlist",
        )

    return True, None, f"Action '{proposal.action_type}' is in executable allowlist"


def check_retry_and_chronic_invariants(
    proposal: RecoveryDecisionProposal,
    target: GatewayTargetContext,
    policy: GatewayPolicy = DEFAULT_GATEWAY_POLICY,
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 5: Independent defense-in-depth enforcement of retry limits and chronic decline blocks."""
    # Invariant 1: Exhausted attempts
    if target.target_attempt_count >= (policy.max_target_attempts + 1):
        return (
            False,
            GatewayReasonCode.BLOCK_RETRY_LIMIT_EXCEEDED,
            f"Target attempt count ({target.target_attempt_count}) >= retry limit threshold ({policy.max_target_attempts + 1})",
        )

    # Invariant 2: Chronic failure history
    if (
        target.customer_history_count >= 3
        and target.customer_success_rate_bps < 2500
        and target.latest_failure_code in policy.blocked_decline_codes
    ):
        return (
            False,
            GatewayReasonCode.BLOCK_CHRONIC_FAILURE_INVARIANT,
            f"Chronic failure pattern ({target.customer_success_rate_bps} bps < 2500 bps) with decline code '{target.latest_failure_code}'",
        )

    return True, None, "Retry and chronic decline safety invariants satisfied"


def check_failure_category_safety(
    proposal: RecoveryDecisionProposal,
    target: GatewayTargetContext,
    policy: GatewayPolicy = DEFAULT_GATEWAY_POLICY,
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 6: Ensure failure code and action mapping does not attempt unsafe retries."""
    # Hard unmitigated fraud codes
    if target.latest_failure_code in policy.unrecoverable_fraud_codes:
        return (
            False,
            GatewayReasonCode.BLOCK_UNRESOLVED_HARD_DECLINE,
            f"Decline code '{target.latest_failure_code}' represents irreversible hard fraud decline",
        )

    # Generic decline without proven reliable history cannot execute automated retry
    if (
        proposal.action_type == RecoveryActionType.RETRY_PAYMENT
        and target.latest_failure_code in policy.blocked_decline_codes
        and target.customer_success_rate_bps < policy.min_reliable_success_rate_bps
    ):
        return (
            False,
            GatewayReasonCode.BLOCK_UNRESOLVED_HARD_DECLINE,
            f"Decline code '{target.latest_failure_code}' cannot be automatically retried without proven customer reliability",
        )

    return True, None, "Failure category safety checks satisfied"


def check_high_value_and_human_approval(
    proposal: RecoveryDecisionProposal,
    target: GatewayTargetContext,
    config: GatewayConfig,
    approval: Optional[HumanApprovalRecord],
) -> Tuple[bool, Optional[GatewayReasonCode], str]:
    """Stage 7: Enforce human approval requirement for high-value or escalated proposals."""
    is_high_value = target.amount_minor >= config.high_value_threshold_minor
    requires_approval = (
        is_high_value
        or proposal.requires_human_approval
        or proposal.action_type == RecoveryActionType.HUMAN_REVIEW
    )

    if not requires_approval:
        return True, None, "No human approval required for standard-value proposal"

    # Human approval is required
    if approval is None:
        reason_code = (
            GatewayReasonCode.HIGH_VALUE_REQUIRES_REVIEW
            if is_high_value
            else GatewayReasonCode.MISSING_HUMAN_APPROVAL
        )
        return (
            False,
            reason_code,
            f"Proposal requires human approval ({'amount >= threshold' if is_high_value else 'escalated'}) but none was provided",
        )

    # Validate approval token
    if approval.proposal_id != proposal.proposal_id or approval.target_id != proposal.target_id:
        return (
            False,
            GatewayReasonCode.INVALID_HUMAN_APPROVAL,
            f"Human approval record token IDs ({approval.proposal_id}, {approval.target_id}) do not match proposal ({proposal.proposal_id}, {proposal.target_id})",
        )

    if not approval.approval_status:
        return (
            False,
            GatewayReasonCode.INVALID_HUMAN_APPROVAL,
            "Human approval record contains approval_status=False",
        )

    if not approval.approved_by or not approval.approved_by.strip():
        return (
            False,
            GatewayReasonCode.INVALID_HUMAN_APPROVAL,
            "Human approval record missing valid approved_by identity",
        )

    return True, None, f"Human approval verified by {approval.approved_by}"
