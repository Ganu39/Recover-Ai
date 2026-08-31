"""Controlled enumeration types for RecoverAI entities."""

import enum


class PaymentStatus(str, enum.Enum):
    """Payment lifecycle status."""

    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentAttemptStatus(str, enum.Enum):
    """Status of an individual payment attempt."""

    INITIATED = "initiated"
    SUCCESSFUL = "successful"
    FAILED = "failed"


class SubscriptionStatus(str, enum.Enum):
    """Subscription lifecycle status."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    HALTED = "halted"


class RecoveryCaseStatus(str, enum.Enum):
    """Status of a potential revenue recovery case."""

    DETECTED = "detected"
    EVALUATING = "evaluating"
    ACTION_PENDING = "action_pending"
    RECOVERED = "recovered"
    UNRECOVERABLE = "unrecoverable"
    CLOSED = "closed"
