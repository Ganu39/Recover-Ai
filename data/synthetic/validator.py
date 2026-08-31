"""Data quality validator for synthetic datasets."""

from typing import Dict, Set
import uuid

from data.synthetic.models import SyntheticDataset, ValidationResult


class DatasetValidator:
    """Validates structural integrity and database-invariant compliance of synthetic datasets."""

    @staticmethod
    def validate(dataset: SyntheticDataset) -> ValidationResult:
        errors = []
        obs = dataset.observable

        # 1. Check Customer uniqueness and IDs
        customer_ids: Set[uuid.UUID] = set()
        customer_ext_ids: Set[str] = set()
        customer_created_map: Dict[uuid.UUID, object] = {}

        for c in obs.customers:
            if c.id in customer_ids:
                errors.append(f"Duplicate Customer ID: {c.id}")
            customer_ids.add(c.id)

            if c.external_customer_id in customer_ext_ids:
                errors.append(f"Duplicate external_customer_id: {c.external_customer_id}")
            customer_ext_ids.add(c.external_customer_id)

            customer_created_map[c.id] = c.created_at

        # 2. Check Subscription validity
        sub_ids: Set[uuid.UUID] = set()
        sub_ext_ids: Set[str] = set()
        sub_created_map: Dict[uuid.UUID, object] = {}

        for s in obs.subscriptions:
            if s.id in sub_ids:
                errors.append(f"Duplicate Subscription ID: {s.id}")
            sub_ids.add(s.id)

            if s.external_subscription_id in sub_ext_ids:
                errors.append(f"Duplicate external_subscription_id: {s.external_subscription_id}")
            sub_ext_ids.add(s.external_subscription_id)

            if s.customer_id not in customer_ids:
                errors.append(f"Subscription {s.id} references non-existent customer_id: {s.customer_id}")

            if s.amount_minor < 0:
                errors.append(f"Subscription {s.id} has negative amount_minor: {s.amount_minor}")

            if s.customer_id in customer_created_map and s.created_at < customer_created_map[s.customer_id]:
                errors.append(f"Subscription {s.id} created before customer {s.customer_id}")

            sub_created_map[s.id] = s.created_at

        # 3. Check Payment validity
        payment_ids: Set[uuid.UUID] = set()
        payment_ext_ids: Set[str] = set()
        payment_created_map: Dict[uuid.UUID, object] = {}

        for p in obs.payments:
            if p.id in payment_ids:
                errors.append(f"Duplicate Payment ID: {p.id}")
            payment_ids.add(p.id)

            if p.external_payment_id in payment_ext_ids:
                errors.append(f"Duplicate external_payment_id: {p.external_payment_id}")
            payment_ext_ids.add(p.external_payment_id)

            if p.customer_id not in customer_ids:
                errors.append(f"Payment {p.id} references non-existent customer_id: {p.customer_id}")

            if p.amount_minor < 0:
                errors.append(f"Payment {p.id} has negative amount_minor: {p.amount_minor}")

            if p.customer_id in customer_created_map and p.created_at < customer_created_map[p.customer_id]:
                errors.append(f"Payment {p.id} created before customer {p.customer_id}")

            payment_created_map[p.id] = p.created_at

        # 4. Check PaymentAttempt validity
        attempt_ids: Set[uuid.UUID] = set()
        attempts_per_payment: Dict[uuid.UUID, list] = {}

        for att in obs.payment_attempts:
            if att.id in attempt_ids:
                errors.append(f"Duplicate PaymentAttempt ID: {att.id}")
            attempt_ids.add(att.id)

            if att.payment_id not in payment_ids:
                errors.append(f"PaymentAttempt {att.id} references non-existent payment_id: {att.payment_id}")

            if att.attempt_number <= 0:
                errors.append(f"PaymentAttempt {att.id} has non-positive attempt_number: {att.attempt_number}")

            if att.payment_id in payment_created_map and att.attempted_at < payment_created_map[att.payment_id]:
                errors.append(f"PaymentAttempt {att.id} attempted before payment created_at")

            attempts_per_payment.setdefault(att.payment_id, []).append(att.attempt_number)

        # Check attempt sequence ordering per payment
        for pay_id, att_nums in attempts_per_payment.items():
            sorted_nums = sorted(att_nums)
            if sorted_nums != list(range(1, len(sorted_nums) + 1)):
                errors.append(f"Payment {pay_id} has irregular attempt numbers: {att_nums}")

        # 5. Check RecoveryCase validity
        case_ids: Set[uuid.UUID] = set()
        for rc in obs.recovery_cases:
            if rc.id in case_ids:
                errors.append(f"Duplicate RecoveryCase ID: {rc.id}")
            case_ids.add(rc.id)

            # Invariant: exactly one target
            has_payment = rc.payment_id is not None
            has_subscription = rc.subscription_id is not None
            if not (has_payment ^ has_subscription):
                errors.append(
                    f"RecoveryCase {rc.id} violates exactly-one target constraint: "
                    f"payment_id={rc.payment_id}, subscription_id={rc.subscription_id}"
                )

            if has_payment and rc.payment_id not in payment_ids:
                errors.append(f"RecoveryCase {rc.id} references non-existent payment_id: {rc.payment_id}")

            if has_subscription and rc.subscription_id not in sub_ids:
                errors.append(f"RecoveryCase {rc.id} references non-existent subscription_id: {rc.subscription_id}")

            if rc.amount_at_risk_minor < 0:
                errors.append(f"RecoveryCase {rc.id} has negative amount_at_risk_minor: {rc.amount_at_risk_minor}")

        # 6. Check Ground Truth consistency
        gt_case_ids = {gt.case_id for gt in dataset.ground_truth}
        if gt_case_ids != case_ids:
            errors.append(f"Ground truth case count ({len(gt_case_ids)}) mismatch with RecoveryCases ({len(case_ids)})")

        return ValidationResult(is_valid=(len(errors) == 0), errors=errors)
