"""Data contracts, enums, and schemas for Recovery Decision Agent (Phase 5)."""

import enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

from agents.diagnosis.schemas import AIDiagnosisResult

DECISION_VERSION = "v1"
POLICY_VERSION = "v1"


class RecoveryActionType(str, enum.Enum):
    """Controlled taxonomy of recovery intervention proposals."""

    NO_ACTION = "NO_ACTION"                                      # Unrecoverable (chronic declines, exhausted retries)
    RETRY_PAYMENT = "RETRY_PAYMENT"                              # Automated retry (transient switch glitch with history)
    RETRY_LATER = "RETRY_LATER"                                  # Scheduled retry candidate (insufficient funds / cooldown)
    REQUEST_PAYMENT_METHOD_UPDATE = "REQUEST_PAYMENT_METHOD_UPDATE"# Customer update link (expired card, new user drop-off)
    SUBSCRIPTION_RECOVERY_WORKFLOW = "SUBSCRIPTION_RECOVERY_WORKFLOW"# Recurring subscription recovery workflow
    HUMAN_REVIEW = "HUMAN_REVIEW"                                # Escalation to operations team


class DecisionStatus(str, enum.Enum):
    """Lifecycle status of the recovery decision proposal."""

    PROPOSED = "PROPOSED"                # Action eligible and approved for execution processing
    REQUIRES_REVIEW = "REQUIRES_REVIEW"  # Action blocked from automated processing; human review required
    BLOCKED = "BLOCKED"                  # Action strictly prohibited by safety invariants
    NO_ACTION = "NO_ACTION"              # No recovery intervention warranted


class ExplanationChain(BaseModel):
    """Structured, inspectable decision explanation chain."""

    observed_facts: List[str] = Field(default_factory=list)
    ai_inferences: List[str] = Field(default_factory=list)
    policy_checks: List[str] = Field(default_factory=list)
    final_rationale: str


class DecisionInputContext(BaseModel):
    """Explicit input contract for recovery decision synthesis."""

    case_id: Optional[uuid.UUID] = None
    target_type: str  # "payment" | "subscription"
    target_id: uuid.UUID
    customer_id: uuid.UUID
    amount_minor: int  # in integer minor units (paise)
    currency: str  # "INR"
    amount_display: str  # e.g., "₹1,500.00"
    customer_history_count: int
    customer_success_count: int
    customer_success_rate_bps: int
    target_attempt_count: int
    latest_failure_code: Optional[str] = None
    subscription_status: Optional[str] = None
    ai_diagnosis: Optional[AIDiagnosisResult] = None


class RecoveryDecisionProposal(BaseModel):
    """Structured recovery decision proposal."""

    decision_version: str = DECISION_VERSION
    policy_version: str = POLICY_VERSION
    proposal_id: uuid.UUID
    case_id: Optional[uuid.UUID] = None
    target_type: str
    target_id: uuid.UUID
    amount_minor: int
    currency: str
    amount_display: str
    action_type: RecoveryActionType
    decision_status: DecisionStatus
    explanation: ExplanationChain
    cooldown_required: bool = False
    requires_human_approval: bool = False
    blocking_conditions: List[str] = Field(default_factory=list)
