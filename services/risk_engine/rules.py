"""Deterministic ruleset and evaluation logic for Baseline Version v1."""

from typing import List, Tuple

from services.risk_engine.models import (
    BASELINE_VERSION,
    ObservableRiskContext,
    RiskEvidence,
    RiskLevel,
    RiskReasonCode,
)

HIGH_VALUE_THRESHOLD_MINOR = 500000  # ₹5,000 in paise


def evaluate_rules_v1(ctx: ObservableRiskContext) -> Tuple[bool, RiskLevel, List[RiskEvidence]]:
    """Evaluate an observable risk context using Baseline Version v1 rules."""
    evidence: List[RiskEvidence] = []

    # 1. Evaluate High-Value Exposure (Signal/Prioritization)
    is_high_value = ctx.amount_at_risk_minor >= HIGH_VALUE_THRESHOLD_MINOR
    if is_high_value:
        evidence.append(
            RiskEvidence(
                reason_code=RiskReasonCode.RC_HIGH_VALUE_EXPOSURE,
                description=f"Transaction value ({ctx.amount_at_risk_minor} paise) exceeds high-value threshold.",
                observed_metric=f"amount={ctx.amount_at_risk_minor}",
            )
        )

    # 2. Evaluate Negative Invariants (Precedence 1)
    has_negative_invariant = False

    # Rule 1: Exhausted Consecutive Attempts
    if ctx.target_attempt_count >= 3:
        has_negative_invariant = True
        evidence.append(
            RiskEvidence(
                reason_code=RiskReasonCode.RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS,
                description=f"Payment has {ctx.target_attempt_count} consecutive failed attempts.",
                observed_metric=f"attempts={ctx.target_attempt_count}",
            )
        )

    # Rule 2: Chronic Decline History
    if (
        ctx.customer_history_count >= 3
        and ctx.customer_success_rate_bps < 2500
        and ctx.latest_failure_code in ("generic_decline", "unknown_failure")
    ):
        has_negative_invariant = True
        evidence.append(
            RiskEvidence(
                reason_code=RiskReasonCode.RC_CHRONIC_DECLINE_HISTORY,
                description=f"Customer has low historical success rate ({ctx.customer_success_rate_bps} bps) across {ctx.customer_history_count} payments.",
                observed_metric=f"success_rate_bps={ctx.customer_success_rate_bps}",
            )
        )

    # 3. Evaluate Recoverability Decision Policy
    if has_negative_invariant:
        predicted_recoverable = False
    else:
        has_positive_signal = False

        # Rule 3: Subscription Billing Glitch
        if ctx.target_type == "subscription" and ctx.subscription_status == "past_due":
            has_positive_signal = True
            evidence.append(
                RiskEvidence(
                    reason_code=RiskReasonCode.RC_SUBSCRIPTION_BILLING_GLITCH,
                    description="Subscription transitioned to past_due billing state.",
                    observed_metric=f"subscription_status={ctx.subscription_status}",
                )
            )

        # Rule 4: Proven History + Transient Failure
        if (
            ctx.customer_history_count >= 2
            and ctx.customer_success_rate_bps >= 7500
            and ctx.latest_failure_code in ("temporary_failure", "generic_decline")
        ):
            has_positive_signal = True
            evidence.append(
                RiskEvidence(
                    reason_code=RiskReasonCode.RC_TRANSIENT_FAILURE_PROVEN_HISTORY,
                    description=f"Strong customer history ({ctx.customer_success_rate_bps} bps) affected by transient decline ({ctx.latest_failure_code}).",
                    observed_metric=f"history_count={ctx.customer_history_count}, failure={ctx.latest_failure_code}",
                )
            )

        # Rule 5: Insufficient Funds (Candidate for retry / balance top-up)
        if ctx.latest_failure_code == "insufficient_funds" and ctx.target_attempt_count <= 2:
            has_positive_signal = True
            evidence.append(
                RiskEvidence(
                    reason_code=RiskReasonCode.RC_INSUFFICIENT_FUNDS,
                    description="Payment declined due to insufficient funds on actionable attempt.",
                    observed_metric=f"failure_code={ctx.latest_failure_code}, attempts={ctx.target_attempt_count}",
                )
            )

        # Rule 6: New Customer Checkout Drop-Off
        if ctx.customer_history_count <= 1 and ctx.target_attempt_count <= 2:
            has_positive_signal = True
            evidence.append(
                RiskEvidence(
                    reason_code=RiskReasonCode.RC_FIRST_TIME_CHECKOUT_DROP,
                    description="New customer checkout drop-off with minimal prior history.",
                    observed_metric=f"history_count={ctx.customer_history_count}, attempts={ctx.target_attempt_count}",
                )
            )

        if has_positive_signal:
            predicted_recoverable = True
        else:
            predicted_recoverable = False
            evidence.append(
                RiskEvidence(
                    reason_code=RiskReasonCode.RC_UNRESOLVED_HARD_DECLINE,
                    description="Unclassified decline or insufficient recovery signals.",
                    observed_metric=f"failure={ctx.latest_failure_code}",
                )
            )

    # 4. Evaluate Risk Level (Severity / Financial Exposure)
    if is_high_value:
        risk_level = RiskLevel.CRITICAL if not predicted_recoverable else RiskLevel.HIGH
    elif not predicted_recoverable:
        reason_codes = {ev.reason_code for ev in evidence}
        if (
            RiskReasonCode.RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS in reason_codes
            or RiskReasonCode.RC_CHRONIC_DECLINE_HISTORY in reason_codes
        ):
            risk_level = RiskLevel.CRITICAL
        else:
            risk_level = RiskLevel.HIGH
    else:
        reason_codes = {ev.reason_code for ev in evidence}
        if RiskReasonCode.RC_TRANSIENT_FAILURE_PROVEN_HISTORY in reason_codes:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.MEDIUM

    return predicted_recoverable, risk_level, evidence
