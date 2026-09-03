"""Structured, immutable in-memory audit logger for the Safety Gateway (Phase 6)."""

import threading
from typing import List, Optional
import uuid

from agents.gateway.schemas import GatewayAuditRecord


class GatewayAuditLogger:
    """Thread-safe, append-only in-memory audit log for gateway evaluations.
    
    Zero database persistence in Phase 6. Records are strictly air-gapped from
    ground-truth evaluation metadata and raw LLM tokens.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[GatewayAuditRecord] = []

    def record(self, audit_record: GatewayAuditRecord) -> None:
        """Append an immutable audit entry."""
        with self._lock:
            self._records.append(audit_record)

    def get_all_records(self) -> List[GatewayAuditRecord]:
        """Return a copy of all audit records."""
        with self._lock:
            return list(self._records)

    def get_by_proposal_id(self, proposal_id: uuid.UUID) -> List[GatewayAuditRecord]:
        """Retrieve audit entries associated with a specific proposal UUID."""
        with self._lock:
            return [r for r in self._records if r.proposal_id == proposal_id]

    def get_by_audit_reference(self, audit_reference: uuid.UUID) -> Optional[GatewayAuditRecord]:
        """Retrieve a specific audit entry by its unique audit reference."""
        with self._lock:
            for r in self._records:
                if r.audit_reference == audit_reference:
                    return r
            return None

    def clear(self) -> None:
        """Reset the audit log (for testing isolation)."""
        with self._lock:
            self._records.clear()
