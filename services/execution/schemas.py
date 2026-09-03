"""Data contracts, enums, and schemas for Bounded Recovery Execution Layer (Phase 7)."""

from datetime import datetime
import enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, StrictInt, StrictStr

from agents.decision.schemas import DECISION_VERSION, POLICY_VERSION, RecoveryActionType, RecoveryDecisionProposal
from agents.gateway.schemas import (
    GATEWAY_VERSION,
    GatewayDecision,
    GatewayDecisionResult,
    GatewayReasonCode,
    GatewayTargetContext,
)


class ExecutionStatus(str, enum.Enum):
    """Controlled execution lifecycle statuses."""

    AUTHORIZED = "AUTHORIZED"                        # Passed Phase 6 safety gateway; eligible for execution
    EXECUTION_STARTED = "EXECUTION_STARTED"          # Execution locked and recorded
    PROVIDER_REQUESTED = "PROVIDER_REQUESTED"        # Dispatched to payment provider adapter
    SUCCEEDED = "SUCCEEDED"                          # Provider returned explicit success
    FAILED = "FAILED"                                # Provider returned terminal failure/decline
    UNKNOWN_PROVIDER_STATE = "UNKNOWN_PROVIDER_STATE"# Ambiguous response or timeout; requires reconciliation
    REQUIRES_REVIEW = "REQUIRES_REVIEW"              # Mismatch or irreconcilable state
    RECONCILED = "RECONCILED"                        # Verified and finalized via webhook or query
    DEFERRED = "DEFERRED"                            # Held for scheduled cooldown (RETRY_LATER)


class PaymentExecutionMode(str, enum.Enum):
    """Allowed payment provider execution environments."""

    TEST = "test"              # Razorpay Test Mode (rzp_test_...)
    SIMULATION = "simulation"  # Deterministic Mock simulation


class ProviderNormalizedStatus(str, enum.Enum):
    """Normalized provider status responses."""

    SUCCESS = "SUCCESS"
    DECLINED = "DECLINED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_PROVIDER_STATE = "UNKNOWN_PROVIDER_STATE"


class ExecutionConfig(BaseModel):
    """Configuration for Phase 7 Execution Service."""

    payment_mode: PaymentExecutionMode = PaymentExecutionMode.TEST
    gateway_version: StrictStr = GATEWAY_VERSION
    policy_version: StrictStr = POLICY_VERSION
    decision_version: StrictStr = DECISION_VERSION
    max_execution_attempts: int = 2
    razorpay_key_id: Optional[StrictStr] = None
    razorpay_key_secret: Optional[StrictStr] = None
    webhook_secret: Optional[StrictStr] = None


class ExecutionRequest(BaseModel):
    """Explicit input contract for executing an authorized recovery action."""

    proposal: RecoveryDecisionProposal
    target: GatewayTargetContext
    gateway_result: GatewayDecisionResult
    idempotency_key: Optional[str] = None
    notes: Optional[str] = None


class ProviderRequest(BaseModel):
    """Normalized payload dispatched to payment provider adapter."""

    idempotency_key: str
    target_type: str
    target_id: uuid.UUID
    customer_id: uuid.UUID
    amount_minor: StrictInt
    currency: StrictStr
    action_type: RecoveryActionType
    receipt: Optional[str] = None
    notes: Dict[str, str] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    """Normalized response received from payment provider adapter."""

    provider_reference: Optional[str] = None
    normalized_status: ProviderNormalizedStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_details: Dict[str, Any] = Field(default_factory=dict)


class ExecutionRecord(BaseModel):
    """Complete execution record representing an authorized execution attempt."""

    execution_id: uuid.UUID
    proposal_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    customer_id: uuid.UUID
    action_type: RecoveryActionType
    amount_minor: int
    currency: str
    status: ExecutionStatus
    attempt_number: int
    provider_reference: Optional[str] = None
    idempotency_key: str
    created_at_iso: str
    updated_at_iso: str
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None


class WebhookPayload(BaseModel):
    """Incoming webhook payload model."""

    event_id: str
    event: str
    payload: Dict[str, Any]
    signature: str
    raw_body: bytes
    received_at_iso: str


class ReconciliationResult(BaseModel):
    """Result of reconciling an execution against provider state."""

    execution_id: uuid.UUID
    previous_status: ExecutionStatus
    reconciled_status: ExecutionStatus
    amount_recovered_minor: int = 0
    provider_reference: Optional[str] = None
    reconciliation_notes: str


class ExecutionBenchmarkReport(BaseModel):
    """Benchmark scorecard for Phase 7 Execution Layer."""

    execution_mode: str
    total_proposals_received: int = 0
    authorized_for_execution: int = 0
    executions_attempted: int = 0
    executions_succeeded: int = 0
    executions_failed: int = 0
    executions_deferred: int = 0
    executions_unknown_state: int = 0
    executions_reconciled: int = 0

    # Financial breakdown (paise)
    amount_at_risk_minor: int = 0
    authorized_amount_minor: int = 0
    attempted_amount_minor: int = 0
    provider_confirmed_amount_minor: int = 0
    recovered_amount_minor: int = 0
    failed_amount_minor: int = 0

    # Critical Safety Release Metrics
    unauthorized_execution_rate_bps: int = 0   # MUST BE 0
    duplicate_execution_rate_bps: int = 0      # MUST BE 0
    financial_integrity_violation_rate_bps: int = 0 # MUST BE 0
