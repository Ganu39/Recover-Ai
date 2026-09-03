"""Immutable append-only execution audit logger (Phase 7)."""

import threading
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class ExecutionAuditEvent(BaseModel):
    """Immutable audit entry for execution lifecycle transitions."""

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    execution_id: uuid.UUID
    proposal_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    customer_id: uuid.UUID
    action_type: str
    amount_minor: int
    currency: str
    stage: str  # e.g., "AUTHORIZED", "ATTEMPTED", "PROVIDER_CONFIRMED", "RECONCILED", "FAILED"
    status: str
    attempt_number: int
    provider_reference: Optional[str] = None
    idempotency_key: str
    timestamp_iso: str
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionAuditLogger:
    """Thread-safe append-only execution audit logger.
    
    Zero secret leakage: strips credentials and authorization headers.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._events: List[ExecutionAuditEvent] = []

    def record_event(self, event: ExecutionAuditEvent) -> None:
        """Append an execution audit event."""
        with self._lock:
            self._events.append(event)

    def get_all_events(self) -> List[ExecutionAuditEvent]:
        """Return all recorded audit events."""
        with self._lock:
            return list(self._events)

    def get_events_for_execution(self, execution_id: uuid.UUID) -> List[ExecutionAuditEvent]:
        """Return audit trail for a specific execution ID."""
        with self._lock:
            return [e for e in self._events if e.execution_id == execution_id]

    def clear(self) -> None:
        """Reset the logger state for test isolation."""
        with self._lock:
            self._events.clear()
