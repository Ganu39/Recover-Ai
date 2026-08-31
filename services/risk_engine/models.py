"""Data contracts, enums, and evaluation models for the deterministic revenue-risk engine."""

import enum
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

BASELINE_VERSION = "v1"


class RiskLevel(str, enum.Enum):
    """Severity and financial exposure priority level."""

    LOW = "LOW"          # High recovery confidence / minimal friction
    MEDIUM = "MEDIUM"    # Actionable recovery opportunity
    HIGH = "HIGH"        # Low recovery confidence / high friction
    CRITICAL = "CRITICAL"# Severe exposure / exhausted attempts / chronic failure


class RiskReasonCode(str, enum.Enum):
    """Observable evidence reason codes."""

    RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS = "RC_EXHAUSTED_CONSECUTIVE_ATTEMPTS"
    RC_CHRONIC_DECLINE_HISTORY = "RC_CHRONIC_DECLINE_HISTORY"
    RC_TRANSIENT_FAILURE_PROVEN_HISTORY = "RC_TRANSIENT_FAILURE_PROVEN_HISTORY"
    RC_INSUFFICIENT_FUNDS = "RC_INSUFFICIENT_FUNDS"
    RC_SUBSCRIPTION_BILLING_GLITCH = "RC_SUBSCRIPTION_BILLING_GLITCH"
    RC_FIRST_TIME_CHECKOUT_DROP = "RC_FIRST_TIME_CHECKOUT_DROP"
    RC_HIGH_VALUE_EXPOSURE = "RC_HIGH_VALUE_EXPOSURE"
    RC_UNRESOLVED_HARD_DECLINE = "RC_UNRESOLVED_HARD_DECLINE"


class RiskEvidence(BaseModel):
    """Structured evidence item justifying baseline evaluation decision."""

    reason_code: RiskReasonCode
    description: str
    observed_metric: str


class ObservableRiskContext(BaseModel):
    """Observable features extracted strictly from production entities."""

    case_id: Optional[uuid.UUID] = None
    target_type: str  # "payment" | "subscription"
    target_id: uuid.UUID
    customer_id: uuid.UUID
    amount_at_risk_minor: int  # in integer minor units (paise)
    currency: str  # "INR"
    customer_history_count: int  # total historical transactions
    customer_success_count: int  # successful historical transactions
    customer_success_rate_bps: int  # 0 to 10000 bps
    target_attempt_count: int  # Number of attempts for current Payment (0 for Subscriptions)
    latest_failure_code: Optional[str] = None
    subscription_status: Optional[str] = None


class RiskEvaluationResult(BaseModel):
    """Deterministic risk evaluation output."""

    baseline_version: str = BASELINE_VERSION
    case_id: Optional[uuid.UUID] = None
    target_type: str
    target_id: uuid.UUID
    predicted_recoverable: bool
    risk_level: RiskLevel
    amount_at_risk_minor: int
    currency: str
    evidence: List[RiskEvidence] = Field(default_factory=list)


class EvaluationMetrics(BaseModel):
    """Aggregate baseline evaluation report comparing predictions against ground truth."""

    baseline_version: str
    dataset_seed: Optional[int] = None
    evaluated_cases_count: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision_bps: int  # in basis points (0-10000 bps)
    recall_bps: int     # in basis points (0-10000 bps)
    f1_score_bps: int   # in basis points (0-10000 bps)
    accuracy_bps: int   # in basis points (0-10000 bps)
    total_amount_at_risk_minor: int          # in paise
    recoverable_amount_captured_minor: int   # TP amount in paise
    recoverable_amount_missed_minor: int     # FN amount in paise
    false_intervention_amount_minor: int     # FP amount in paise
    revenue_capture_rate_bps: int            # Captured / Total Recoverable in bps
    rule_firing_counts: Dict[str, int] = Field(default_factory=dict)
