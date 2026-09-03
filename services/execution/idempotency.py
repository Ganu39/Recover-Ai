"""Deterministic execution idempotency and concurrency protection (Phase 7)."""

import threading
from typing import Dict, Optional, Tuple
import uuid

from services.execution.schemas import ExecutionRecord


def derive_execution_idempotency_key(
    proposal_id: uuid.UUID,
    gateway_version: str,
    policy_version: str,
    action_type: str,
) -> str:
    """Deterministically derive logical execution idempotency key using UUID5."""
    seed_str = f"recoverai-exec-{proposal_id}-{gateway_version}-{policy_version}-{action_type}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed_str))


class ExecutionIdempotencyManager:
    """Thread-safe, atomic execution registry preventing duplicate charges under concurrent requests."""

    def __init__(self):
        self._lock = threading.Lock()
        # idempotency_key -> ExecutionRecord
        self._records: Dict[str, ExecutionRecord] = {}
        # Keys currently under active in-flight execution
        self._in_flight: set[str] = set()

    def check_existing(self, idempotency_key: str) -> Optional[ExecutionRecord]:
        """Retrieve existing execution record for key, if present."""
        with self._lock:
            return self._records.get(idempotency_key)

    def start_execution(self, idempotency_key: str) -> Tuple[bool, Optional[ExecutionRecord]]:
        """Atomically acquire execution lock.
        
        Returns:
            (can_proceed: bool, existing_record: Optional[ExecutionRecord])
        """
        with self._lock:
            if idempotency_key in self._records:
                return False, self._records[idempotency_key]

            if idempotency_key in self._in_flight:
                # Concurrent request already in progress
                return False, None

            self._in_flight.add(idempotency_key)
            return True, None

    def complete_execution(self, record: ExecutionRecord) -> None:
        """Store finished execution record and release in-flight lock."""
        with self._lock:
            self._records[record.idempotency_key] = record
            self._in_flight.discard(record.idempotency_key)

    def release_lock(self, idempotency_key: str) -> None:
        """Release in-flight lock without storing (e.g. on early validation abort)."""
        with self._lock:
            self._in_flight.discard(idempotency_key)

    def clear(self) -> None:
        """Reset state for test isolation."""
        with self._lock:
            self._records.clear()
            self._in_flight.clear()
