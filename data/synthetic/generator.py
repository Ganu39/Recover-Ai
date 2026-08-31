"""Deterministic synthetic transaction and recovery scenario generator."""

import random
import uuid
from datetime import timedelta
from typing import Dict, List, Tuple

from data.models import (
    Customer,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
    Subscription,
    SubscriptionStatus,
)
from data.synthetic.models import (
    CustomerProfileType,
    GeneratorConfig,
    ObservableDataset,
    RecoveryGroundTruth,
    ScenarioType,
    SyntheticDataset,
)
from data.synthetic.profiles import PROFILES
from data.synthetic.scenarios import SCENARIO_SPECS


class SyntheticDataGenerator:
    """Generates deterministic datasets with realistic customer histories and hidden ground truth."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.rng = random.Random(config.seed)

    def _generate_uuid(self) -> uuid.UUID:
        """Generate a deterministic UUID from the RNG state."""
        return uuid.UUID(bytes=self.rng.randbytes(16), version=4)

    def _sample_scenario_type(self) -> ScenarioType:
        """Deterministically sample a scenario archetype based on integer basis point weights."""
        total_weight = sum(self.config.scenario_weights.values())
        choice_val = self.rng.randint(0, total_weight - 1)
        cumulative = 0
        for scenario_type, weight in self.config.scenario_weights.items():
            cumulative += weight
            if choice_val < cumulative:
                return scenario_type
        return ScenarioType.HIGH_PROBABILITY_RECOVERABLE

    def generate(self) -> SyntheticDataset:
        """Generate the complete synthetic dataset."""
        customers: List[Customer] = []
        customer_profiles: Dict[uuid.UUID, CustomerProfileType] = {}
        all_profile_types = list(CustomerProfileType)

        # 1. Generate exact N Customers
        for i in range(self.config.num_customers):
            cust_id = self._generate_uuid()
            profile_type = all_profile_types[i % len(all_profile_types)]
            customer_profiles[cust_id] = profile_type

            # Deterministic offset within first 30 days
            created_offset_secs = self.rng.randint(0, 30 * 86400)
            created_at = self.config.dataset_start_date + timedelta(seconds=created_offset_secs)

            customer = Customer(
                id=cust_id,
                external_customer_id=f"cust_syn_{i+1:06d}",
                email=f"user_{i+1:06d}@synthetic.recoverai.internal",
                name=f"Synthetic Customer {i+1}",
                created_at=created_at,
                updated_at=created_at,
            )
            customers.append(customer)

        # 2. Generate Subscriptions for a fraction of customers
        subscriptions: List[Subscription] = []
        sub_counter = 1
        for customer in customers:
            if self.rng.randint(0, 9999) < self.config.subscription_ratio_bps:
                sub_id = self._generate_uuid()
                profile = PROFILES[customer_profiles[customer.id]]
                sub_created_at = customer.created_at + timedelta(seconds=self.rng.randint(3600, 86400 * 5))
                amount_minor = self.rng.randint(profile.min_amount_minor, profile.max_amount_minor)

                subscription = Subscription(
                    id=sub_id,
                    external_subscription_id=f"sub_syn_{sub_counter:06d}",
                    customer_id=customer.id,
                    amount_minor=amount_minor,
                    currency="INR",
                    status=SubscriptionStatus.ACTIVE,
                    interval="monthly",
                    created_at=sub_created_at,
                    updated_at=sub_created_at,
                )
                subscriptions.append(subscription)
                sub_counter += 1

        # 3. Generate exactly M Payments distributed across Customers
        payments: List[Payment] = []
        payment_attempts: List[PaymentAttempt] = []
        failed_payments: List[Tuple[Payment, CustomerProfileType]] = []

        # Allocate payments to customers
        customer_payment_counts = [0] * len(customers)
        for p_idx in range(self.config.num_payments):
            # Prioritize customers with larger historical caps
            c_idx = p_idx % len(customers)
            customer_payment_counts[c_idx] += 1

        payment_counter = 1
        for c_idx, customer in enumerate(customers):
            num_cust_payments = customer_payment_counts[c_idx]
            profile_type = customer_profiles[customer.id]
            profile = PROFILES[profile_type]

            current_time = customer.created_at
            for _ in range(num_cust_payments):
                current_time += timedelta(seconds=self.rng.randint(3600, 86400 * 10))
                pay_id = self._generate_uuid()
                amount_minor = self.rng.randint(profile.min_amount_minor, profile.max_amount_minor)

                # Determine payment success via integer basis points
                is_success = self.rng.randint(0, 9999) < profile.success_rate_bps

                if is_success:
                    payment_status = PaymentStatus.CAPTURED
                else:
                    payment_status = PaymentStatus.FAILED

                payment = Payment(
                    id=pay_id,
                    external_payment_id=f"pay_syn_{payment_counter:07d}",
                    customer_id=customer.id,
                    amount_minor=amount_minor,
                    currency="INR",
                    status=payment_status,
                    created_at=current_time,
                    updated_at=current_time,
                )
                payments.append(payment)

                # Generate attempts for this payment
                if is_success:
                    # Successful payment usually has 1 successful attempt
                    attempt_id = self._generate_uuid()
                    attempt = PaymentAttempt(
                        id=attempt_id,
                        payment_id=payment.id,
                        attempt_number=1,
                        status=PaymentAttemptStatus.SUCCESSFUL,
                        failure_code=None,
                        failure_reason=None,
                        attempted_at=current_time + timedelta(seconds=5),
                    )
                    payment_attempts.append(attempt)
                else:
                    # Failed payment may have 1 to 3 attempts
                    num_attempts = self.rng.randint(1, 3)
                    for att_num in range(1, num_attempts + 1):
                        att_time = current_time + timedelta(seconds=att_num * 120)
                        failure_code = self.rng.choice([
                            "temporary_failure",
                            "insufficient_funds",
                            "expired_payment_method",
                            "generic_decline",
                            "unknown_failure",
                        ])
                        attempt = PaymentAttempt(
                            id=self._generate_uuid(),
                            payment_id=payment.id,
                            attempt_number=att_num,
                            status=PaymentAttemptStatus.FAILED,
                            failure_code=failure_code,
                            failure_reason=f"Gateway decline: {failure_code}",
                            attempted_at=att_time,
                        )
                        payment_attempts.append(attempt)

                    failed_payments.append((payment, profile_type))

                payment_counter += 1

        # 4. Generate Recovery Cases and Hidden Evaluation Ground Truth
        recovery_cases: List[RecoveryCase] = []
        ground_truth_records: List[RecoveryGroundTruth] = []

        # Generate from failed payments
        for payment, profile_type in failed_payments:
            scenario_type = self._sample_scenario_type()
            spec = SCENARIO_SPECS[scenario_type]

            # Payment-based scenario
            if spec.target_type == "payment":
                rc_id = self._generate_uuid()
                detected_at = payment.created_at + timedelta(seconds=300)
                rc = RecoveryCase(
                    id=rc_id,
                    payment_id=payment.id,
                    subscription_id=None,
                    status=RecoveryCaseStatus.DETECTED,
                    amount_at_risk_minor=payment.amount_minor,
                    currency=payment.currency,
                    detected_at=detected_at,
                    resolved_at=None,
                )
                recovery_cases.append(rc)

                gt = RecoveryGroundTruth(
                    case_id=rc_id,
                    target_type="payment",
                    target_id=payment.id,
                    scenario_type=scenario_type,
                    is_recoverable=spec.is_recoverable,
                    expected_recovery_reason=spec.expected_recovery_reason,
                )
                ground_truth_records.append(gt)

        # Generate subscription recovery scenarios from subscriptions
        sub_spec = SCENARIO_SPECS[ScenarioType.SUBSCRIPTION_FAILURE]
        for subscription in subscriptions:
            # Fraction of subscriptions encounter a past_due billing failure
            if self.rng.randint(0, 9999) < 2000:  # 20% of subscriptions fail
                subscription.status = SubscriptionStatus.PAST_DUE
                rc_id = self._generate_uuid()
                detected_at = subscription.created_at + timedelta(days=30, seconds=600)
                rc = RecoveryCase(
                    id=rc_id,
                    payment_id=None,
                    subscription_id=subscription.id,
                    status=RecoveryCaseStatus.DETECTED,
                    amount_at_risk_minor=subscription.amount_minor,
                    currency=subscription.currency,
                    detected_at=detected_at,
                    resolved_at=None,
                )
                recovery_cases.append(rc)

                gt = RecoveryGroundTruth(
                    case_id=rc_id,
                    target_type="subscription",
                    target_id=subscription.id,
                    scenario_type=ScenarioType.SUBSCRIPTION_FAILURE,
                    is_recoverable=sub_spec.is_recoverable,
                    expected_recovery_reason=sub_spec.expected_recovery_reason,
                )
                ground_truth_records.append(gt)

        observable = ObservableDataset(
            customers=customers,
            payments=payments,
            payment_attempts=payment_attempts,
            subscriptions=subscriptions,
            recovery_cases=recovery_cases,
        )

        return SyntheticDataset(
            config=self.config,
            observable=observable,
            ground_truth=ground_truth_records,
        )
