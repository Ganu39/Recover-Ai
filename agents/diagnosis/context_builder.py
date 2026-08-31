"""Deterministic observable context builder for AI Root-Cause Diagnosis."""

from typing import Dict, List, Optional
import uuid

from data.models import Customer, Payment, PaymentAttempt, RecoveryCase, Subscription
from data.models.enums import PaymentStatus
from data.synthetic.models import ObservableDataset
from agents.diagnosis.schemas import AIDiagnosisInputContext, AttemptSummary


def format_amount_display(amount_minor: int, currency: str = "INR") -> str:
    """Format integer minor units (paise) into human-readable currency display string."""
    rupees = amount_minor / 100.0
    if currency == "INR":
        return f"₹{rupees:,.2f}"
    return f"{currency} {rupees:,.2f}"


def mask_identifier(entity_id: uuid.UUID, prefix: str) -> str:
    """Mask UUIDs for privacy and context compactness (e.g., cust_...a1b2)."""
    hex_str = entity_id.hex
    return f"{prefix}_...{hex_str[-4:]}"


class AIDiagnosisContextBuilder:
    """Transforms observable database entities into sanitized AI input contexts."""

    @staticmethod
    def build_from_dataset(observable: ObservableDataset) -> List[AIDiagnosisInputContext]:
        """Extract canonical AI diagnosis contexts from an ObservableDataset."""
        customer_map: Dict[uuid.UUID, Customer] = {c.id: c for c in observable.customers}
        payment_map: Dict[uuid.UUID, Payment] = {p.id: p for p in observable.payments}
        sub_map: Dict[uuid.UUID, Subscription] = {s.id: s for s in observable.subscriptions}

        cust_payments: Dict[uuid.UUID, List[Payment]] = {}
        for p in observable.payments:
            cust_payments.setdefault(p.customer_id, []).append(p)

        payment_attempts: Dict[uuid.UUID, List[PaymentAttempt]] = {}
        for att in observable.payment_attempts:
            payment_attempts.setdefault(att.payment_id, []).append(att)

        contexts: List[AIDiagnosisInputContext] = []

        for rc in observable.recovery_cases:
            if rc.payment_id is not None:
                payment = payment_map[rc.payment_id]
                customer = customer_map[payment.customer_id]

                # Historical transactions strictly prior to current payment
                prior_payments = sorted(
                    [p for p in cust_payments.get(customer.id, []) if p.created_at < payment.created_at],
                    key=lambda x: x.created_at,
                )
                history_count = len(prior_payments)
                success_count = sum(1 for p in prior_payments if p.status == PaymentStatus.CAPTURED)
                success_rate_pct = (success_count * 100) // history_count if history_count > 0 else 0

                # Customer tenure in days relative to payment creation
                tenure_days = max(0, (payment.created_at - customer.created_at).days)

                # Attempts for current payment (canonical chronological order)
                raw_attempts = sorted(
                    payment_attempts.get(payment.id, []),
                    key=lambda a: a.attempt_number,
                )
                attempt_summaries = [
                    AttemptSummary(
                        attempt_number=a.attempt_number,
                        failure_code=a.failure_code,
                        failure_reason=a.failure_reason,
                        attempt_offset_seconds=int((a.attempted_at - payment.created_at).total_seconds()),
                    )
                    for a in raw_attempts
                ]

                ctx = AIDiagnosisInputContext(
                    case_id=rc.id,
                    target_type="payment",
                    target_id=payment.id,
                    masked_target_id=mask_identifier(payment.id, "pay"),
                    masked_customer_id=mask_identifier(customer.id, "cust"),
                    amount_minor=payment.amount_minor,
                    currency=payment.currency,
                    amount_display=format_amount_display(payment.amount_minor, payment.currency),
                    customer_tenure_days=tenure_days,
                    customer_history_count=history_count,
                    customer_success_count=success_count,
                    customer_historical_success_rate_pct=success_rate_pct,
                    attempts=attempt_summaries,
                    subscription_status=None,
                )
                contexts.append(ctx)

            elif rc.subscription_id is not None:
                subscription = sub_map[rc.subscription_id]
                customer = customer_map[subscription.customer_id]

                prior_payments = sorted(
                    [p for p in cust_payments.get(customer.id, []) if p.created_at < subscription.created_at],
                    key=lambda x: x.created_at,
                )
                history_count = len(prior_payments)
                success_count = sum(1 for p in prior_payments if p.status == PaymentStatus.CAPTURED)
                success_rate_pct = (success_count * 100) // history_count if history_count > 0 else 0

                tenure_days = max(0, (subscription.created_at - customer.created_at).days)

                ctx = AIDiagnosisInputContext(
                    case_id=rc.id,
                    target_type="subscription",
                    target_id=subscription.id,
                    masked_target_id=mask_identifier(subscription.id, "sub"),
                    masked_customer_id=mask_identifier(customer.id, "cust"),
                    amount_minor=subscription.amount_minor,
                    currency=subscription.currency,
                    amount_display=format_amount_display(subscription.amount_minor, subscription.currency),
                    customer_tenure_days=tenure_days,
                    customer_history_count=history_count,
                    customer_success_count=success_count,
                    customer_historical_success_rate_pct=success_rate_pct,
                    attempts=[],
                    subscription_status=subscription.status.value,
                )
                contexts.append(ctx)

        return contexts
