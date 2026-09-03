"""Deterministic Execution State Machine for Phase 7."""

from typing import Dict, Set

from services.execution.schemas import ExecutionStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal or unauthorized execution state transition is attempted."""
    pass


class ExecutionStateMachine:
    """Enforces deterministic execution lifecycle transitions."""

    LEGAL_TRANSITIONS: Dict[ExecutionStatus, Set[ExecutionStatus]] = {
        ExecutionStatus.AUTHORIZED: {
            ExecutionStatus.EXECUTION_STARTED,
            ExecutionStatus.DEFERRED,
            ExecutionStatus.REQUIRES_REVIEW,
        },
        ExecutionStatus.EXECUTION_STARTED: {
            ExecutionStatus.PROVIDER_REQUESTED,
            ExecutionStatus.FAILED,
            ExecutionStatus.REQUIRES_REVIEW,
        },
        ExecutionStatus.PROVIDER_REQUESTED: {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.UNKNOWN_PROVIDER_STATE,
            ExecutionStatus.REQUIRES_REVIEW,
        },
        ExecutionStatus.UNKNOWN_PROVIDER_STATE: {
            ExecutionStatus.RECONCILED,
            ExecutionStatus.FAILED,
            ExecutionStatus.REQUIRES_REVIEW,
        },
        ExecutionStatus.SUCCEEDED: {
            ExecutionStatus.RECONCILED,
            ExecutionStatus.FAILED,
            ExecutionStatus.REQUIRES_REVIEW,
        },
        ExecutionStatus.DEFERRED: {
            ExecutionStatus.EXECUTION_STARTED,
            ExecutionStatus.REQUIRES_REVIEW,
        },
        ExecutionStatus.FAILED: set(),
        ExecutionStatus.RECONCILED: set(),
        ExecutionStatus.REQUIRES_REVIEW: set(),
    }

    @classmethod
    def can_transition(cls, from_status: ExecutionStatus, to_status: ExecutionStatus) -> bool:
        """Check if transition from from_status to to_status is legally defined."""
        allowed = cls.LEGAL_TRANSITIONS.get(from_status, set())
        return to_status in allowed

    @classmethod
    def validate_transition(cls, from_status: ExecutionStatus, to_status: ExecutionStatus) -> None:
        """Validate state transition; raise InvalidStateTransitionError if illegal."""
        if not cls.can_transition(from_status, to_status):
            raise InvalidStateTransitionError(
                f"Illegal state transition attempted: {from_status.value} -> {to_status.value}. "
                f"Allowed destinations: {[s.value for s in cls.LEGAL_TRANSITIONS.get(from_status, set())]}"
            )
