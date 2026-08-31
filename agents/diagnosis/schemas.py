"""Schemas, taxonomies, and contracts for AI Root-Cause Diagnosis (Phase 4)."""

import enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field


class DiagnosisCategory(str, enum.Enum):
    """Controlled taxonomy of payment failure root causes."""

    TRANSIENT_SYSTEM_ERROR = "transient_system_error"        # Gateway switch / timeout / network glitch
    BALANCE_OR_LIMIT_DEFICIT = "balance_or_limit_deficit"    # Insufficient funds or card limit reached
    EXPIRED_OR_INVALID_METHOD = "expired_or_invalid_method"  # Expired card or invalid mandate
    PERSISTENT_ISSUER_DECLINE = "persistent_issuer_decline"  # Hard card decline / exhausted retries
    SUBSCRIPTION_BILLING_ISSUE = "subscription_billing_issue"# Past due recurring subscription billing
    FIRST_TIME_USER_DROP = "first_time_user_drop"            # First-time checkout friction
    INSUFFICIENT_DATA = "insufficient_data"                  # Unclear / ambiguous observable signals


class QualitativeConfidence(str, enum.Enum):
    """Categorical qualitative confidence level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DiagnosisStatus(str, enum.Enum):
    """Execution status of the AI diagnosis pipeline."""

    SUCCESS = "SUCCESS"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TIMEOUT = "TIMEOUT"


class EvidenceItem(BaseModel):
    """Structured evidence linking an observed fact to its input source and deduction."""

    fact: str = Field(description="Strictly verified fact from input context")
    source_field: str = Field(description="Observable source field name")
    inference: str = Field(description="Logical deduction drawn from the fact")


class AttemptSummary(BaseModel):
    """Chronological summary of a payment attempt."""

    attempt_number: int
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    attempt_offset_seconds: int = 0


class AIDiagnosisInputContext(BaseModel):
    """Deterministic, sanitized observable context sent to LLM prompt builder."""

    case_id: Optional[uuid.UUID] = None
    target_type: str  # "payment" | "subscription"
    target_id: uuid.UUID
    masked_target_id: str
    masked_customer_id: str
    amount_minor: int  # in integer minor units (paise)
    currency: str  # "INR"
    amount_display: str  # e.g., "₹1,500.00"
    customer_tenure_days: int
    customer_history_count: int
    customer_success_count: int
    customer_historical_success_rate_pct: int
    attempts: List[AttemptSummary] = Field(default_factory=list)
    subscription_status: Optional[str] = None


class AIDiagnosisPayload(BaseModel):
    """Raw structured output schema requested from untrusted LLM response."""

    diagnosis_category: DiagnosisCategory
    diagnosis_summary: str
    observed_facts: List[str] = Field(default_factory=list)
    evidence_reasoning: List[EvidenceItem] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    ai_recoverability_assessment: bool
    confidence: QualitativeConfidence
    ai_recoverability_reason: str


class AIDiagnosisResult(BaseModel):
    """Trusted application domain result produced after validation and metadata enrichment."""

    prompt_version: str
    provider_name: str
    model_name: str
    latency_ms: int
    status: DiagnosisStatus
    case_id: Optional[uuid.UUID] = None
    target_type: str
    target_id: uuid.UUID
    amount_minor: int
    currency: str
    diagnosis_category: DiagnosisCategory
    diagnosis_summary: str
    observed_facts: List[str] = Field(default_factory=list)
    evidence_reasoning: List[EvidenceItem] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    ai_recoverability_assessment: Optional[bool] = None
    confidence: QualitativeConfidence
    ai_recoverability_reason: str
    error_message: Optional[str] = None
