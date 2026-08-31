"""Deterministic Recovery Policy definitions and safety evaluation rules (Version v1)."""

from typing import Set
from pydantic import BaseModel, Field

from agents.decision.schemas import POLICY_VERSION


class RecoveryPolicy(BaseModel):
    """Configurable deterministic safety policy rules."""

    policy_version: str = POLICY_VERSION
    max_retry_attempts: int = 2  # Payments with >= 3 attempts are strictly blocked
    high_value_threshold_minor: int = 500000  # ₹5,000 in paise (escalate to human review)
    min_reliable_history_count: int = 2
    min_reliable_success_rate_bps: int = 7500  # 75.00%
    blocked_decline_codes: Set[str] = Field(
        default_factory=lambda: {"generic_decline", "unknown_failure"}
    )


DEFAULT_RECOVERY_POLICY = RecoveryPolicy()
