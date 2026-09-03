"""Cryptographic webhook handler and state reconciliation (Phase 7)."""

import json
import threading
from typing import Any, Dict, Optional, Set, Tuple
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
    """Handles incoming payment gateway webhooks with cryptographic verification and replay protection."""

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
        event_id_header: Optional[str] = None,
        received_at_iso: str = "2026-09-03T10:00:00Z",
    ) -> Tuple[bool, str, Optional[ReconciliationResult]]:
        """Verify, deduplicate, and reconcile an incoming provider webhook.
        
        Returns:
            (success: bool, code: str, result: Optional[ReconciliationResult])
        """
        # 1. Cryptographic signature verification over raw body
        if not signature or not webhook_secret or not raw_body:
            return False, "INVALID_SIGNATURE", None

        if not self.provider.verify_webhook_signature(raw_body, signature, webhook_secret):
            return False, "INVALID_SIGNATURE", None

        # 2. Parse payload JSON safely
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return False, "MALFORMED_JSON_PAYLOAD", None

        # 3. Webhook Deduplication & Replay Protection
        # Prefer X-Razorpay-Event-Id header, then payload id/event_id, then deterministic body hash
        event_id = (
            event_id_header
            or payload.get("id")
            or payload.get("event_id")
            or str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_body.decode("utf-8", errors="ignore")))
        )
        event_type = payload.get("event", "unknown")

        with self._lock:
            if event_id in self._processed_events:
                return True, "IDEMPOTENT_REPLAY", None
            self._processed_events.add(event_id)

        # 4. Extract provider entity references from standard Razorpay payload structures
        payload_container = payload.get("payload", {})
        payment_entity = payload_container.get("payment", {}).get("entity", {})
        order_entity = payload_container.get("order", {}).get("entity", {})
        plink_entity = payload_container.get("payment_link", {}).get("entity", {})

        payment_id = payment_entity.get("id")
        order_id = payment_entity.get("order_id") or order_entity.get("id")
        plink_id = plink_entity.get("id") or payment_entity.get("payment_link_id")
        generic_ref = payload.get("provider_reference")

        candidate_refs = {ref for ref in [payment_id, order_id, plink_id, generic_ref] if ref}

        if not candidate_refs:
            return False, "MISSING_PROVIDER_REFERENCE", None

        # 5. Locate matching execution record in registry
        target_record: Optional[ExecutionRecord] = None
        for record in self.idempotency_manager._records.values():
            if record.provider_reference in candidate_refs:
                target_record = record
                break

        if target_record is None:
            return False, "UNKNOWN_EXECUTION_REFERENCE", None

        # 6. Idempotent check if record is already reconciled
        if target_record.status == ExecutionStatus.RECONCILED and event_type in {
            "payment.captured",
            "order.paid",
            "payment_link.paid",
        }:
            return True, "ALREADY_RECONCILED", ReconciliationResult(
                execution_id=target_record.execution_id,
                previous_status=ExecutionStatus.RECONCILED,
                reconciled_status=ExecutionStatus.RECONCILED,
                amount_recovered_minor=target_record.amount_minor,
                provider_reference=target_record.provider_reference,
                reconciliation_notes=f"Idempotent: execution {target_record.execution_id} is already reconciled.",
            )

        # 7. Financial Integrity Verification: Amount and Currency Check
        entity = payment_entity or order_entity or plink_entity or {}
        incoming_amount = entity.get("amount")
        incoming_currency = entity.get("currency")

        if incoming_amount is not None:
            if not isinstance(incoming_amount, int) or incoming_amount != target_record.amount_minor:
                return False, "AMOUNT_MISMATCH", None

        if incoming_currency is not None:
            if incoming_currency != target_record.currency:
                return False, "CURRENCY_MISMATCH", None

        # 8. State Reconciliation
        previous_status = target_record.status
        if event_type in {"payment.captured", "order.paid", "payment_link.paid"}:
            new_status = ExecutionStatus.RECONCILED
            amount_recovered = target_record.amount_minor
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
            provider_reference=target_record.provider_reference,
            reconciliation_notes=f"Reconciled via verified Razorpay webhook event '{event_type}'.",
        )

        # Audit event with zero secret leakage
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
                stage="RECONCILED" if new_status == ExecutionStatus.RECONCILED else "FAILED",
                status=new_status.value,
                attempt_number=target_record.attempt_number,
                provider_reference=target_record.provider_reference,
                idempotency_key=target_record.idempotency_key,
                timestamp_iso=received_at_iso,
                metadata={
                    "event_type": event_type,
                    "event_id": event_id,
                    "provider": "Razorpay Test Mode",
                },
            )
        )

        return True, "RECONCILED_SUCCESSFULLY", reconciliation

