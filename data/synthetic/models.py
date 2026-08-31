"""Data structures and configuration models for the synthetic transaction engine."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from data.models import (
    Customer,
    Payment,
    PaymentAttempt,
    RecoveryCase,
    Subscription,
)


class CustomerProfileType(str, enum.Enum):
    """Behavioral profile types for synthetic customers."""

    RELIABLE = "reliable"
    INTERMITTENT = "intermittent"
    HIGH_VALUE = "high_value"
    CHRONIC_FAILURE = "chronic_failure"
    NEW_CUSTOMER = "new_customer"


class ScenarioType(str, enum.Enum):
    """Recovery scenario archetype identifiers."""

    HIGH_PROBABILITY_RECOVERABLE = "high_probability_recoverable"
    LOW_PROBABILITY_RECOVERABLE = "low_probability_recoverable"
    CLEARLY_NON_RECOVERABLE = "clearly_non_recoverable"
    NEW_CUSTOMER = "new_customer"
    REPEATED_FAILURE = "repeated_failure"
    TEMPORARY_FAILURE_AFTER_SUCCESS_HISTORY = "temporary_failure_after_success_history"
    SUBSCRIPTION_FAILURE = "subscription_failure"
    HIGH_VALUE_PAYMENT_FAILURE = "high_value_payment_failure"


DEFAULT_SCENARIO_WEIGHTS: Dict[ScenarioType, int] = {
    ScenarioType.HIGH_PROBABILITY_RECOVERABLE: 2000,
    ScenarioType.LOW_PROBABILITY_RECOVERABLE: 1500,
    ScenarioType.CLEARLY_NON_RECOVERABLE: 1500,
    ScenarioType.NEW_CUSTOMER: 1000,
    ScenarioType.REPEATED_FAILURE: 1000,
    ScenarioType.TEMPORARY_FAILURE_AFTER_SUCCESS_HISTORY: 1500,
    ScenarioType.SUBSCRIPTION_FAILURE: 1000,
    ScenarioType.HIGH_VALUE_PAYMENT_FAILURE: 500,
}


class GeneratorConfig(BaseModel):
    """Configuration for deterministic synthetic data generation."""

    seed: int = Field(default=42, description="RNG seed for reproducibility")
    num_customers: int = Field(default=1000, description="Exact number of customers to generate")
    num_payments: int = Field(default=5000, description="Exact number of payments to generate")
    subscription_ratio_bps: int = Field(
        default=2500,
        description="Basis points of customers with subscriptions (2500 = 25%)",
    )
    dataset_start_date: datetime = Field(
        default_factory=lambda: datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        description="Fixed reference start timestamp for chronological determinism",
    )
    scenario_weights: Dict[ScenarioType, int] = Field(
        default_factory=lambda: DEFAULT_SCENARIO_WEIGHTS.copy(),
        description="Configurable integer weights in basis points for scenario distribution",
    )


class RecoveryGroundTruth(BaseModel):
    """Hidden evaluation metadata. Strictly separated from production models."""

    case_id: uuid.UUID
    target_type: str  # "payment" or "subscription"
    target_id: uuid.UUID
    scenario_type: ScenarioType
    is_recoverable: bool
    expected_recovery_reason: str


class ObservableDataset(BaseModel):
    """Observable production-compatible dataset available to application & future AI."""

    model_config = {"arbitrary_types_allowed": True}

    customers: List[Customer]
    payments: List[Payment]
    payment_attempts: List[PaymentAttempt]
    subscriptions: List[Subscription]
    recovery_cases: List[RecoveryCase]


class SyntheticDataset(BaseModel):
    """Complete container encapsulating observable entities and hidden ground-truth."""

    model_config = {"arbitrary_types_allowed": True}

    config: GeneratorConfig
    observable: ObservableDataset
    ground_truth: List[RecoveryGroundTruth]


class DatasetStatistics(BaseModel):
    """Reconciled deterministic summary statistics in integer minor units."""

    customers_count: int
    payments_count: int
    successful_payments_count: int
    failed_payments_count: int
    payment_attempts_count: int
    subscriptions_count: int
    recovery_cases_count: int
    recoverable_cases_count: int
    non_recoverable_cases_count: int
    total_payment_amount_minor: int
    failed_payment_amount_minor: int
    amount_at_risk_minor: int
    recoverable_amount_minor: int
    non_recoverable_amount_minor: int
    scenario_counts: Dict[str, int]


class ValidationResult(BaseModel):
    """Validation report indicating dataset integrity status."""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
