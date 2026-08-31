"""Feature context extractor converting observable entities into ObservableRiskContext."""

from typing import Dict, List
import uuid

from data.models import Customer, Payment, PaymentAttempt, RecoveryCase, Subscription
from data.models.enums import PaymentStatus
from data.synthetic.models import ObservableDataset
from services.risk_engine.models import ObservableRiskContext


class ObservableFeatureExtractor:
    """Extracts observable historical and transaction features from production entity collections."""

    @staticmethod
    def extract_from_dataset(observable: ObservableDataset) -> List[ObservableRiskContext]:
        """Extract observable contexts from an in-memory ObservableDataset."""
        customer_map: Dict[uuid.UUID, Customer] = {c.id: c for c in observable.customers}
        payment_map: Dict[uuid.UUID, Payment] = {p.id: p for p in observable.payments}
        sub_map: Dict[uuid.UUID, Subscription] = {s.id: s for s in observable.subscriptions}

        # Index payments and attempts by customer/payment
        cust_payments: Dict[uuid.UUID, List[Payment]] = {}
        for p in observable.payments:
            cust_payments.setdefault(p.customer_id, []).append(p)

        payment_attempts: Dict[uuid.UUID, List[PaymentAttempt]] = {}
        for att in observable.payment_attempts:
            payment_attempts.setdefault(att.payment_id, []).append(att)

        contexts: List[ObservableRiskContext] = []

        for rc in observable.recovery_cases:
            if rc.payment_id is not None:
                payment = payment_map[rc.payment_id]
                customer = customer_map[payment.customer_id]

                # Historical payments prior to current payment
                all_prior = [
                    p for p in cust_payments.get(customer.id, [])
                    if p.created_at < payment.created_at
                ]
                history_count = len(all_prior)
                success_count = sum(1 for p in all_prior if p.status == PaymentStatus.CAPTURED)
                success_rate_bps = (success_count * 10000) // history_count if history_count > 0 else 0

                # Attempts for current payment
                attempts = payment_attempts.get(payment.id, [])
                target_attempt_count = len(attempts)
                latest_failure_code = attempts[-1].failure_code if attempts else None

                ctx = ObservableRiskContext(
                    case_id=rc.id,
                    target_type="payment",
                    target_id=payment.id,
                    customer_id=customer.id,
                    amount_at_risk_minor=rc.amount_at_risk_minor,
                    currency=rc.currency,
                    customer_history_count=history_count,
                    customer_success_count=success_count,
                    customer_success_rate_bps=success_rate_bps,
                    target_attempt_count=target_attempt_count,
                    latest_failure_code=latest_failure_code,
                    subscription_status=None,
                )
                contexts.append(ctx)

            elif rc.subscription_id is not None:
                subscription = sub_map[rc.subscription_id]
                customer = customer_map[subscription.customer_id]

                all_prior = [
                    p for p in cust_payments.get(customer.id, [])
                    if p.created_at < subscription.created_at
                ]
                history_count = len(all_prior)
                success_count = sum(1 for p in all_prior if p.status == PaymentStatus.CAPTURED)
                success_rate_bps = (success_count * 10000) // history_count if history_count > 0 else 0

                ctx = ObservableRiskContext(
                    case_id=rc.id,
                    target_type="subscription",
                    target_id=subscription.id,
                    customer_id=customer.id,
                    amount_at_risk_minor=rc.amount_at_risk_minor,
                    currency=rc.currency,
                    customer_history_count=history_count,
                    customer_success_count=success_count,
                    customer_success_rate_bps=success_rate_bps,
                    target_attempt_count=0,  # Defined as 0 for Subscriptions
                    latest_failure_code=None,
                    subscription_status=subscription.status.value,
                )
                contexts.append(ctx)

        return contexts
