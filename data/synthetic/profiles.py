"""Behavioral profiles for synthetic customer simulation."""

from typing import Dict, NamedTuple
from data.synthetic.models import CustomerProfileType


class ProfileConfig(NamedTuple):
    """Integer-based parameters for customer behavioral profiles."""

    profile_type: CustomerProfileType
    success_rate_bps: int  # e.g., 9000 = 90.00%
    min_amount_minor: int  # in paise
    max_amount_minor: int  # in paise
    min_history_payments: int
    max_history_payments: int


PROFILES: Dict[CustomerProfileType, ProfileConfig] = {
    CustomerProfileType.RELIABLE: ProfileConfig(
        profile_type=CustomerProfileType.RELIABLE,
        success_rate_bps=9000,
        min_amount_minor=50000,   # ₹500
        max_amount_minor=250000,  # ₹2,500
        min_history_payments=3,
        max_history_payments=8,
    ),
    CustomerProfileType.INTERMITTENT: ProfileConfig(
        profile_type=CustomerProfileType.INTERMITTENT,
        success_rate_bps=5500,
        min_amount_minor=30000,   # ₹300
        max_amount_minor=350000,  # ₹3,500
        min_history_payments=2,
        max_history_payments=6,
    ),
    CustomerProfileType.HIGH_VALUE: ProfileConfig(
        profile_type=CustomerProfileType.HIGH_VALUE,
        success_rate_bps=8500,
        min_amount_minor=500000,   # ₹5,000
        max_amount_minor=5000000,  # ₹50,000
        min_history_payments=2,
        max_history_payments=10,
    ),
    CustomerProfileType.CHRONIC_FAILURE: ProfileConfig(
        profile_type=CustomerProfileType.CHRONIC_FAILURE,
        success_rate_bps=1800,
        min_amount_minor=20000,   # ₹200
        max_amount_minor=150000,  # ₹1,500
        min_history_payments=2,
        max_history_payments=7,
    ),
    CustomerProfileType.NEW_CUSTOMER: ProfileConfig(
        profile_type=CustomerProfileType.NEW_CUSTOMER,
        success_rate_bps=7000,
        min_amount_minor=40000,   # ₹400
        max_amount_minor=200000,  # ₹2,000
        min_history_payments=0,
        max_history_payments=1,
    ),
}
