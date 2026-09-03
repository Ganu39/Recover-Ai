"""Data contracts, enums, and schemas for Deterministic Policy & Safety Gateway (Phase 6)."""

import enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, StrictInt, StrictStr

GATEWAY_VERSION = "v1"
POLICY_VERSION = "v1"
DECISION_VERSION = "v1"


class GatewayDecision(str, enum.Enum):
    """Terminal lifecycle decision from the Deterministic Policy & Safety Gateway."""

    APPROVED = "APPROVED"                    # Passed all safety checks; eligible for execution layer
    BLOCKED = "BLOCKED"                      # Strictly prohibited by deterministic safety policy / invariants
    REQUIRES_REVIEW = "REQUIRES_REVIEW"      # Human authorization required (e.g. high-value or ambiguity)
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"# System kill switch engaged; zero execution permitted
    RATE_LIMITED = "RATE_LIMITED"            # Safety rate limit threshold exceeded
    INVALID_PROPOSAL = "INVALID_PROPOSAL"    # Malformed proposal, tampering, schema or version mismatch


class GatewayReasonCode(str, enum.Enum):
    """Controlled, machine-readable reason codes for gateway decisions."""

    APPROVED_FOR_EXECUTION_LAYER = "APPROVED_FOR_EXECUTION_LAYER"
    BLOCK_SCHEMA_VALIDATION_FAILED = "BLOCK_SCHEMA_VALIDATION_FAILED"
    BLOCK_PROPOSAL_IDENTITY_MISMATCH = "BLOCK_PROPOSAL_IDENTITY_MISMATCH"
    BLOCK_NON_EXECUTABLE_ACTION = "BLOCK_NON_EXECUTABLE_ACTION"
    BLOCK_AMOUNT_MISMATCH = "BLOCK_AMOUNT_MISMATCH"
    BLOCK_CURRENCY_MISMATCH = "BLOCK_CURRENCY_MISMATCH"
    BLOCK_INVALID_FINANCIAL_UNIT = "BLOCK_INVALID_FINANCIAL_UNIT"
    BLOCK_RETRY_LIMIT_EXCEEDED = "BLOCK_RETRY_LIMIT_EXCEEDED"
    BLOCK_CHRONIC_FAILURE_INVARIANT = "BLOCK_CHRONIC_FAILURE_INVARIANT"
    BLOCK_UNRESOLVED_HARD_DECLINE = "BLOCK_UNRESOLVED_HARD_DECLINE"
    HIGH_VALUE_REQUIRES_REVIEW = "HIGH_VALUE_REQUIRES_REVIEW"
    AI_AMBIGUITY_REQUIRES_REVIEW = "AI_AMBIGUITY_REQUIRES_REVIEW"
    MISSING_HUMAN_APPROVAL = "MISSING_HUMAN_APPROVAL"
    INVALID_HUMAN_APPROVAL = "INVALID_HUMAN_APPROVAL"
    BLOCK_CONFLICTING_PROPOSAL_FOR_TARGET = "BLOCK_CONFLICTING_PROPOSAL_FOR_TARGET"
    IDEMPOTENT_REPLAY_APPROVED = "IDEMPOTENT_REPLAY_APPROVED"
    IDEMPOTENT_REPLAY_BLOCKED = "IDEMPOTENT_REPLAY_BLOCKED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"
    GATEWAY_CONFIGURATION_ERROR = "GATEWAY_CONFIGURATION_ERROR"
    UNKNOWN_ACTION_TYPE = "UNKNOWN_ACTION_TYPE"


class GatewayTargetContext(BaseModel):
    """Trusted observable context passed to the safety gateway for verification.
    
    Contains strictly observable facts from Phase 1 database or observable synthetic dataset.
    Zero AI diagnosis inferences, zero RecoveryGroundTruth evaluation metadata.
    """

    case_id: Optional[uuid.UUID] = None
    target_type: StrictStr  # "payment" | "subscription"
    target_id: uuid.UUID
    customer_id: uuid.UUID
    amount_minor: StrictInt  # strictly integer paise (e.g. 500000 = ₹5,000.00)
    currency: StrictStr = "INR"
    amount_display: StrictStr
    customer_history_count: StrictInt = 0
    customer_success_count: StrictInt = 0
    customer_success_rate_bps: StrictInt = 0
    target_attempt_count: StrictInt = 0
    latest_failure_code: Optional[StrictStr] = None
    subscription_status: Optional[StrictStr] = None


class HumanApprovalRecord(BaseModel):
    """Explicit trusted human authorization record for high-value or escalated interventions."""

    proposal_id: uuid.UUID
    target_id: uuid.UUID
    approved_by: StrictStr  # e.g., "ops_supervisor_42@recoverai.internal"
    approved_at_iso: StrictStr  # ISO-8601 formatted timestamp
    approval_status: bool = True
    notes: Optional[StrictStr] = None


class GatewayConfig(BaseModel):
    """Configurable safety thresholds and runtime parameters for Gateway v1."""

    gateway_version: StrictStr = GATEWAY_VERSION
    policy_version: StrictStr = POLICY_VERSION
    decision_version: StrictStr = DECISION_VERSION
    kill_switch_active: bool = False
    max_target_attempts: int = 2  # target_attempt_count >= 3 strictly blocked
    high_value_threshold_minor: int = 500000  # ₹5,000 in paise
    rate_limit_per_target_window: int = 3  # max 3 authorizations per target window
    window_seconds: int = 3600  # 1 hour window


class GatewayDecisionResult(BaseModel):
    """Terminal output contract of the Deterministic Policy & Safety Gateway."""

    gateway_decision: GatewayDecision
    proposal_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    decision_reason: str
    reason_code: GatewayReasonCode
    policy_version: str
    gateway_version: str
    decision_version: str
    checks_evaluated: List[str] = Field(default_factory=list)
    checks_passed: List[str] = Field(default_factory=list)
    blocking_conditions: List[str] = Field(default_factory=list)
    audit_reference: uuid.UUID
    eligible_for_execution_layer: bool
    is_replay: bool = False


class GatewayAuditRecord(BaseModel):
    """Immutable audit record generated on every gateway proposal evaluation."""

    audit_reference: uuid.UUID
    evaluated_at_epoch_ms: int
    proposal_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    customer_id: uuid.UUID
    amount_minor: int
    currency: str
    action_type: str
    gateway_decision: GatewayDecision
    reason_code: GatewayReasonCode
    decision_reason: str
    policy_version: str
    gateway_version: str
    decision_version: str
    checks_evaluated: List[str]
    checks_passed: List[str]
    blocking_conditions: List[str]
    eligible_for_execution_layer: bool
    is_replay: bool
