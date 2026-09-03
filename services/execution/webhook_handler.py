"""Cryptographic webhook handler and state reconciliation (Phase 7)."""

import json
import threading
from typing import Dict, Optional, Set, Tuple
import uuid

from services.execution.audit import ExecutionAuditEvent, ExecutionAuditLogger
from services.execution.idempotency import ExecutionIdempotencyManager
from services.execution.provider import BasePaymentProvider
from services.execution.schemas import (
    ExecutionRecord,
    ExecutionStatus,
    ReconciliationResult,
)
from services.execution.state_machine import ExecutionStateMachine


class WebhookHandler:
    """Handles incoming payment gateway webhooks with signature verification and replay protection."""

    def __init__(
        self,
        provider: BasePaymentProvider,
        idempotency_manager: ExecutionIdempotencyManager,
        audit_logger: Optional[ExecutionAuditLogger] = None,
    ):
        self.provider = provider
        self.idempotency_manager = idempotency_manager
        self.audit_logger = audit_logger or ExecutionAuditLogger()
        self._lock = threading.Lock()
        self._processed_events: Set[str] = set()

    def handle_webhook(
        self,
        raw_body: bytes,
        signature: str,
        webhook_secret: str,
        received_at_iso: str = "2026-09-03T10:00:00Z",
    ) -> Tuple[bool, str, Optional[ReconciliationResult]]:
        """Verify, deduplicate, and process an incoming provider webhook.
        
        Returns:
            (success: bool, code: str, result: Optional[ReconciliationResult])
        """
        # 1. Cryptographic signature verification
        if not self.provider.verify_webhook_signature(raw_body, signature, webhook_secret):
            return False, "INVALID_SIGNATURE", None

        # 2. Parse payload
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return False, "MALFORMED_JSON_PAYLOAD", None

        event_id = payload.get("id") or payload.get("event_id") or str(uuid.uuid5(uuid.NAMESPACE_DNS, str(raw_body)))
        event_type = payload.get("event", "unknown")

        # 3. Webhook Replay Protection
        with self._lock:
            if event_id in self._processed_events:
                return True, "IDEMPOTENT_REPLAY", None
            self._processed_events.add(event_id)

        # 4. Extract provider reference and payload details
        payload_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        provider_ref = payload_entity.get("id") or payload.get("provider_reference")

        if not provider_ref:
            return False, "MISSING_PROVIDER_REFERENCE", None

        # 5. Locate matching execution record
        target_record: Optional[ExecutionRecord] = None
        for record in self.idempotency_manager._records.values():
            if record.provider_reference == provider_ref:
                target_record = record
                break

        if target_record is None:
            return False, "UNKNOWN_EXECUTION_REFERENCE", None

        # 6. State Reconciliation
        previous_status = target_record.status
        if event_type in {"payment.captured", "order.paid"}:
            new_status = ExecutionStatus.RECONCILED
            amount_recovered = payload_entity.get("amount", target_record.amount_minor)
        elif event_type in {"payment.failed"}:
            new_status = ExecutionStatus.FAILED
            amount_recovered = 0
        else:
            return True, f"IGNORED_EVENT_TYPE_{event_type}", None

        # Validate legal transition
        try:
            ExecutionStateMachine.validate_transition(previous_status, new_status)
        except Exception as exc:
            return False, f"INVALID_STATE_TRANSITION: {exc}", None

        # Update record
        target_record.status = new_status
        target_record.updated_at_iso = received_at_iso

        reconciliation = ReconciliationResult(
            execution_id=target_record.execution_id,
            previous_status=previous_status,
            reconciled_status=new_status,
            amount_recovered_minor=amount_recovered,
            provider_reference=provider_ref,
            reconciliation_notes=f"Reconciled via webhook event '{event_type}'.",
        )

        self.audit_logger.record_event(
            ExecutionAuditEvent(
                execution_id=target_record.execution_id,
                proposal_id=target_record.proposal_id,
                target_type=target_record.target_type,
                target_id=target_record.target_id,
                customer_id=target_record.customer_id,
                action_type=target_record.action_type.value,
                amount_minor=target_record.amount_minor,
                currency=target_record.currency,
                stage="RECONCILED",
                status=new_status.value,
                attempt_number=target_record.attempt_number,
                provider_reference=provider_ref,
                idempotency_key=target_record.idempotency_key,
                timestamp_iso=received_at_iso,
                metadata={"event_type": event_type, "event_id": event_id},
            )
        )

        return True, "RECONCILED_SUCCESSFULLY", reconciliation
