"""Deterministic in-memory idempotency and replay protection store (Phase 6)."""

import threading
from typing import Dict, Optional, Tuple
import uuid

from agents.gateway.schemas import (
    GatewayDecision,
    GatewayDecisionResult,
    GatewayReasonCode,
)


class InMemoryIdempotencyStore:
    """Thread-safe, deterministic in-memory idempotency registry.
    
    Prevents duplicate downstream authorizations, protects against replay attacks,
    and detects conflicting proposals for the same underlying transaction target.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Primary lookup: (proposal_id_str, gateway_version, policy_version) -> GatewayDecisionResult
        self._primary_store: Dict[Tuple[str, str, str], GatewayDecisionResult] = {}
        # Target lookup: (target_type, target_id_str) -> (proposal_id_str, action_type, amount_minor, GatewayDecisionResult)
        self._target_store: Dict[Tuple[str, str], Tuple[str, str, int, GatewayDecisionResult]] = {}

    def get_existing_decision(
        self,
        proposal_id: uuid.UUID,
        gateway_version: str,
        policy_version: str,
    ) -> Optional[GatewayDecisionResult]:
        """Retrieve existing decision result for exact proposal/version tuple."""
        with self._lock:
            key = (str(proposal_id), gateway_version, policy_version)
            return self._primary_store.get(key)

    def get_stored_target_entry(
        self,
        target_type: str,
        target_id: uuid.UUID,
    ) -> Optional[Tuple[str, str, int, GatewayDecisionResult]]:
        """Retrieve stored entry for target if exists."""
        with self._lock:
            target_key = (target_type, str(target_id))
            return self._target_store.get(target_key)

    def check_target_conflict(
        self,
        target_type: str,
        target_id: uuid.UUID,
        proposal_id: uuid.UUID,
        action_type: str,
        amount_minor: int,
    ) -> Optional[Tuple[GatewayReasonCode, str]]:
        """Evaluate deterministic target conflict rule.
        
        Deterministic Conflict Rule:
        A conflict occurs if an execution-eligible (APPROVED) proposal already exists for the
        exact (target_type, target_id) with a DIFFERENT proposal_id and either:
        1. A DIFFERENT action_type (e.g. RETRY_PAYMENT vs REQUEST_PAYMENT_METHOD_UPDATE), OR
        2. A DIFFERENT amount_minor (conflicting financial assertion).
        
        Legitimate non-conflicting scenarios:
        - Exact proposal_id (handled by primary idempotency replay).
        - Prior proposal for the target was BLOCKED, allowing an updated or revised proposal.
        """
        with self._lock:
            target_key = (target_type, str(target_id))
            existing = self._target_store.get(target_key)
            if not existing:
                return None

            existing_proposal_id, existing_action, existing_amount, existing_result = existing

            if existing_proposal_id != str(proposal_id):
                if existing_result.gateway_decision == GatewayDecision.APPROVED:
                    if existing_action != action_type or existing_amount != amount_minor:
                        return (
                            GatewayReasonCode.BLOCK_CONFLICTING_PROPOSAL_FOR_TARGET,
                            f"Target {target_type}:{target_id} already has an APPROVED proposal ({existing_proposal_id}) "
                            f"with action '{existing_action}' and amount {existing_amount} paise. "
                            f"Conflicting proposal ({proposal_id}) with action '{action_type}' and amount {amount_minor} paise rejected.",
                        )
            return None

    def record_decision(
        self,
        proposal_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        action_type: str,
        amount_minor: int,
        gateway_version: str,
        policy_version: str,
        decision_result: GatewayDecisionResult,
    ) -> None:
        """Atomically record decision in idempotency store."""
        with self._lock:
            key = (str(proposal_id), gateway_version, policy_version)
            self._primary_store[key] = decision_result
            target_key = (target_type, str(target_id))
            self._target_store[target_key] = (
                str(proposal_id),
                action_type,
                amount_minor,
                decision_result,
            )

    def clear(self) -> None:
        """Reset store (primarily for unit test isolation)."""
        with self._lock:
            self._primary_store.clear()
            self._target_store.clear()
