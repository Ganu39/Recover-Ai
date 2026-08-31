"""Canonical scenario rules and definitions for recovery opportunities."""

from typing import Dict, List, NamedTuple
from data.synthetic.models import CustomerProfileType, ScenarioType


class ScenarioSpec(NamedTuple):
    """Specification defining scenario generation behavior and ground-truth rules."""

    scenario_type: ScenarioType
    target_type: str  # "payment" or "subscription"
    is_recoverable: bool
    expected_recovery_reason: str
    allowed_failure_codes: List[str]
    applicable_profiles: List[CustomerProfileType]
    min_attempts: int
    max_attempts: int


SCENARIO_SPECS: Dict[ScenarioType, ScenarioSpec] = {
    ScenarioType.HIGH_PROBABILITY_RECOVERABLE: ScenarioSpec(
        scenario_type=ScenarioType.HIGH_PROBABILITY_RECOVERABLE,
        target_type="payment",
        is_recoverable=True,
        expected_recovery_reason="Transient network or issuer glitch with high customer intent and historical reliability.",
        allowed_failure_codes=["temporary_failure", "generic_decline"],
        applicable_profiles=[
            CustomerProfileType.RELIABLE,
            CustomerProfileType.INTERMITTENT,
            CustomerProfileType.HIGH_VALUE,
        ],
        min_attempts=1,
        max_attempts=2,
    ),
    ScenarioType.LOW_PROBABILITY_RECOVERABLE: ScenarioSpec(
        scenario_type=ScenarioType.LOW_PROBABILITY_RECOVERABLE,
        target_type="payment",
        is_recoverable=True,
        expected_recovery_reason="Expired payment method or temporary balance deficit requiring customer intervention.",
        allowed_failure_codes=["expired_payment_method", "insufficient_funds"],
        applicable_profiles=[
            CustomerProfileType.INTERMITTENT,
            CustomerProfileType.RELIABLE,
        ],
        min_attempts=1,
        max_attempts=1,
    ),
    ScenarioType.CLEARLY_NON_RECOVERABLE: ScenarioSpec(
        scenario_type=ScenarioType.CLEARLY_NON_RECOVERABLE,
        target_type="payment",
        is_recoverable=False,
        expected_recovery_reason="Hard card decline / invalid instrument with absence of alternative payment methods.",
        allowed_failure_codes=["generic_decline", "unknown_failure"],
        applicable_profiles=[
            CustomerProfileType.CHRONIC_FAILURE,
            CustomerProfileType.INTERMITTENT,
        ],
        min_attempts=1,
        max_attempts=2,
    ),
    ScenarioType.NEW_CUSTOMER: ScenarioSpec(
        scenario_type=ScenarioType.NEW_CUSTOMER,
        target_type="payment",
        is_recoverable=True,
        expected_recovery_reason="First-time customer checkout drop-off recoverable via checkout link or alternate payment method.",
        allowed_failure_codes=["insufficient_funds", "temporary_failure"],
        applicable_profiles=[CustomerProfileType.NEW_CUSTOMER],
        min_attempts=1,
        max_attempts=1,
    ),
    ScenarioType.REPEATED_FAILURE: ScenarioSpec(
        scenario_type=ScenarioType.REPEATED_FAILURE,
        target_type="payment",
        is_recoverable=False,
        expected_recovery_reason="Exhausted repeated attempts with persistent issuer refusal.",
        allowed_failure_codes=["insufficient_funds", "generic_decline"],
        applicable_profiles=[
            CustomerProfileType.CHRONIC_FAILURE,
            CustomerProfileType.INTERMITTENT,
            CustomerProfileType.RELIABLE,
        ],
        min_attempts=3,
        max_attempts=4,
    ),
    ScenarioType.TEMPORARY_FAILURE_AFTER_SUCCESS_HISTORY: ScenarioSpec(
        scenario_type=ScenarioType.TEMPORARY_FAILURE_AFTER_SUCCESS_HISTORY,
        target_type="payment",
        is_recoverable=True,
        expected_recovery_reason="Strong historical payment track record affected by transient technical failure.",
        allowed_failure_codes=["temporary_failure"],
        applicable_profiles=[
            CustomerProfileType.RELIABLE,
            CustomerProfileType.HIGH_VALUE,
        ],
        min_attempts=1,
        max_attempts=1,
    ),
    ScenarioType.SUBSCRIPTION_FAILURE: ScenarioSpec(
        scenario_type=ScenarioType.SUBSCRIPTION_FAILURE,
        target_type="subscription",
        is_recoverable=True,
        expected_recovery_reason="Recurring billing failure recoverable via smart retry schedule or update payment link.",
        allowed_failure_codes=["insufficient_funds", "temporary_failure", "expired_payment_method"],
        applicable_profiles=[
            CustomerProfileType.RELIABLE,
            CustomerProfileType.INTERMITTENT,
            CustomerProfileType.HIGH_VALUE,
        ],
        min_attempts=1,
        max_attempts=2,
    ),
    ScenarioType.HIGH_VALUE_PAYMENT_FAILURE: ScenarioSpec(
        scenario_type=ScenarioType.HIGH_VALUE_PAYMENT_FAILURE,
        target_type="payment",
        is_recoverable=True,
        expected_recovery_reason="High-value order failure with strong customer intent justifying high-priority recovery intervention.",
        allowed_failure_codes=["temporary_failure", "insufficient_funds"],
        applicable_profiles=[CustomerProfileType.HIGH_VALUE],
        min_attempts=1,
        max_attempts=2,
    ),
}
