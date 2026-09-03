"""Gateway Policy definitions, action allowlists, and safety threshold rules (Phase 6)."""

from typing import Set
from pydantic import BaseModel, Field

from agents.decision.schemas import RecoveryActionType
from agents.gateway.schemas import GATEWAY_VERSION, POLICY_VERSION

# Strict action allowlist: Only these actions may ever reach eligible_for_execution_layer=True
EXECUTABLE_ACTION_ALLOWLIST: Set[RecoveryActionType] = {
    RecoveryActionType.RETRY_PAYMENT,
    RecoveryActionType.RETRY_LATER,
    RecoveryActionType.REQUEST_PAYMENT_METHOD_UPDATE,
    RecoveryActionType.SUBSCRIPTION_RECOVERY_WORKFLOW,
}

# Strictly prohibited from automated execution without human/supervisory conversion
NON_EXECUTABLE_ACTIONS: Set[RecoveryActionType] = {
    RecoveryActionType.NO_ACTION,
    RecoveryActionType.HUMAN_REVIEW,
}


class GatewayPolicy(BaseModel):
    """Deterministic safety thresholds and invariant constraints for the Gateway."""

    gateway_version: str = GATEWAY_VERSION
    policy_version: str = POLICY_VERSION
    max_target_attempts: int = 2  # target_attempt_count >= 3 strictly blocked
    high_value_threshold_minor: int = 500000  # ₹5,000 in paise (500,000 paise)
    min_reliable_history_count: int = 2
    min_reliable_success_rate_bps: int = 7500
    blocked_decline_codes: Set[str] = Field(
        default_factory=lambda: {"generic_decline", "unknown_failure"}
    )
    unrecoverable_fraud_codes: Set[str] = Field(
        default_factory=lambda: {"suspected_fraud", "stolen_card", "lost_card"}
    )


DEFAULT_GATEWAY_POLICY = GatewayPolicy()
