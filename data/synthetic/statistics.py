"""Deterministic summary statistics calculation using integer minor units."""

from collections import Counter
from typing import Dict

from data.models.enums import PaymentStatus
from data.synthetic.models import DatasetStatistics, SyntheticDataset


def calculate_statistics(dataset: SyntheticDataset) -> DatasetStatistics:
    """Calculate reconciled summary statistics using integer arithmetic only."""
    obs = dataset.observable

    total_payment_amount_minor = sum(p.amount_minor for p in obs.payments)
    failed_payments = [p for p in obs.payments if p.status == PaymentStatus.FAILED]
    failed_payment_amount_minor = sum(p.amount_minor for p in failed_payments)
    successful_payments_count = sum(1 for p in obs.payments if p.status == PaymentStatus.CAPTURED)
    amount_at_risk_minor = sum(rc.amount_at_risk_minor for rc in obs.recovery_cases)

    # Recoverable breakdown from evaluation ground truth
    ground_truth_map = {gt.case_id: gt for gt in dataset.ground_truth}
    recoverable_cases_count = sum(1 for gt in dataset.ground_truth if gt.is_recoverable)
    non_recoverable_cases_count = len(dataset.ground_truth) - recoverable_cases_count

    recoverable_amount_minor = 0
    non_recoverable_amount_minor = 0
    for rc in obs.recovery_cases:
        gt = ground_truth_map.get(rc.id)
        if gt and gt.is_recoverable:
            recoverable_amount_minor += rc.amount_at_risk_minor
        else:
            non_recoverable_amount_minor += rc.amount_at_risk_minor

    scenario_counts: Dict[str, int] = dict(Counter(gt.scenario_type.value for gt in dataset.ground_truth))

    return DatasetStatistics(
        customers_count=len(obs.customers),
        payments_count=len(obs.payments),
        successful_payments_count=successful_payments_count,
        failed_payments_count=len(failed_payments),
        payment_attempts_count=len(obs.payment_attempts),
        subscriptions_count=len(obs.subscriptions),
        recovery_cases_count=len(obs.recovery_cases),
        recoverable_cases_count=recoverable_cases_count,
        non_recoverable_cases_count=non_recoverable_cases_count,
        total_payment_amount_minor=total_payment_amount_minor,
        failed_payment_amount_minor=failed_payment_amount_minor,
        amount_at_risk_minor=amount_at_risk_minor,
        recoverable_amount_minor=recoverable_amount_minor,
        non_recoverable_amount_minor=non_recoverable_amount_minor,
        scenario_counts=scenario_counts,
    )
