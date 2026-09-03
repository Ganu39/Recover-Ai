"""Bounded Recovery Execution Service (Phase 7)."""

from datetime import datetime, timezone
from typing import Optional, Tuple
import uuid

from agents.decision.schemas import (
    DECISION_VERSION,
    POLICY_VERSION,
    RecoveryActionType,
    RecoveryDecisionProposal,
)
from agents.gateway.checks import derive_expected_proposal_id
from agents.gateway.policy import EXECUTABLE_ACTION_ALLOWLIST
from agents.gateway.schemas import (
    GATEWAY_VERSION,
    GatewayDecision,
    GatewayDecisionResult,
    GatewayReasonCode,
    GatewayTargetContext,
)
from services.execution.audit import ExecutionAuditEvent, ExecutionAuditLogger
from services.execution.idempotency import (
    ExecutionIdempotencyManager,
    derive_execution_idempotency_key,
)
from services.execution.mock_provider import MockPaymentProvider
from services.execution.provider import BasePaymentProvider
from services.execution.schemas import (
    ExecutionConfig,
    ExecutionRecord,
    ExecutionRequest,
    ExecutionStatus,
    PaymentExecutionMode,
    ProviderNormalizedStatus,
    ProviderRequest,
    ProviderResponse,
)
from services.execution.state_machine import ExecutionStateMachine
from services.execution.webhook_handler import WebhookHandler


class ExecutionAuthorizationError(ValueError):
    """Raised when pre-execution authorization recheck fails."""
    pass


class ConcurrencyConflictError(RuntimeError):
    """Raised when concurrent in-flight execution conflict occurs."""
    pass


class ExecutionService:
    """The authoritative execution service enforcing strict pre-authorization revalidation,
    deterministic idempotency, bounded retries, and provider abstraction.
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        provider: Optional[BasePaymentProvider] = None,
        idempotency_manager: Optional[ExecutionIdempotencyManager] = None,
        audit_logger: Optional[ExecutionAuditLogger] = None,
    ):
        self.config = config or ExecutionConfig()
        self.provider = provider or MockPaymentProvider()
        self.idempotency_manager = idempotency_manager or ExecutionIdempotencyManager()
        self.audit_logger = audit_logger or ExecutionAuditLogger()
        self.webhook_handler = WebhookHandler(
            provider=self.provider,
            idempotency_manager=self.idempotency_manager,
            audit_logger=self.audit_logger,
        )

    def _revalidate_authorization(
        self,
        proposal: RecoveryDecisionProposal,
        target: GatewayTargetContext,
        gw_result: GatewayDecisionResult,
    ) -> None:
        """Independently re-validate Phase 6 authorization immediately prior to execution."""
        # 1. Gateway Decision check
        if gw_result.gateway_decision != GatewayDecision.APPROVED:
            raise ExecutionAuthorizationError(
                f"Gateway decision must be APPROVED. Received: {gw_result.gateway_decision.value}"
            )

        if not gw_result.eligible_for_execution_layer:
            raise ExecutionAuthorizationError("eligible_for_execution_layer is False.")

        if gw_result.reason_code not in {
            GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER,
            GatewayReasonCode.IDEMPOTENT_REPLAY_APPROVED,
        }:
            raise ExecutionAuthorizationError(f"Unauthorized reason code: {gw_result.reason_code.value}")

        # 2. Version Contract Verification
        if (
            proposal.decision_version != DECISION_VERSION
            or proposal.policy_version != POLICY_VERSION
            or gw_result.gateway_version != GATEWAY_VERSION
        ):
            raise ExecutionAuthorizationError("Version contract mismatch across execution layers.")

        # 3. Proposal Identity Verification
        expected_prop_id = derive_expected_proposal_id(
            decision_version=proposal.decision_version,
            policy_version=proposal.policy_version,
            target_type=proposal.target_type,
            target_id=proposal.target_id,
        )
        if proposal.proposal_id != expected_prop_id or gw_result.proposal_id != expected_prop_id:
            raise ExecutionAuthorizationError(
                f"Proposal identity mismatch: {proposal.proposal_id} != expected {expected_prop_id}"
            )

        if proposal.target_id != target.target_id or gw_result.target_id != target.target_id:
            raise ExecutionAuthorizationError("Target ID mismatch across proposal and context.")

        # 3. Financial Integrity Verification
        if proposal.amount_minor != target.amount_minor:
            raise ExecutionAuthorizationError(
                f"Amount mismatch: proposal ({proposal.amount_minor}) != target ({target.amount_minor})"
            )

        if not isinstance(proposal.amount_minor, int) or proposal.amount_minor <= 0:
            raise ExecutionAuthorizationError("Amount must be a strictly positive integer minor unit.")

        if proposal.currency != target.currency or proposal.currency != "INR":
            raise ExecutionAuthorizationError(f"Unsupported or mismatched currency '{proposal.currency}'")

        # 4. Action Allowlist Verification
        if proposal.action_type not in EXECUTABLE_ACTION_ALLOWLIST:
            raise ExecutionAuthorizationError(
                f"Action '{proposal.action_type}' is not in executable allowlist."
            )

        # 5. Version Verification
        if (
            proposal.decision_version != DECISION_VERSION
            or proposal.policy_version != POLICY_VERSION
            or gw_result.gateway_version != GATEWAY_VERSION
        ):
            raise ExecutionAuthorizationError("Version contract mismatch across execution layers.")

        # 6. Retry Ceiling Defense-in-Depth
        if target.target_attempt_count > self.config.max_execution_attempts:
            raise ExecutionAuthorizationError(
                f"Attempt count ({target.target_attempt_count}) exceeds ceiling ({self.config.max_execution_attempts})"
            )

        # 7. Environment & Live-Mode Protection
        if self.config.payment_mode not in {PaymentExecutionMode.TEST, PaymentExecutionMode.SIMULATION}:
            raise ExecutionAuthorizationError(
                f"Execution mode '{self.config.payment_mode}' is prohibited. Live execution is disabled."
            )

    async def execute_recovery(
        self,
        request: ExecutionRequest,
        now_iso: Optional[str] = None,
    ) -> ExecutionRecord:
        """Execute recovery action through provider adapter with persistent idempotency."""
        if now_iso is None:
            now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Pre-execution authorization recheck
        self._revalidate_authorization(
            proposal=request.proposal,
            target=request.target,
            gw_result=request.gateway_result,
        )

        action_str = request.proposal.action_type.value
        idempotency_key = request.idempotency_key or derive_execution_idempotency_key(
            proposal_id=request.proposal.proposal_id,
            gateway_version=self.config.gateway_version,
            policy_version=self.config.policy_version,
            action_type=action_str,
        )

        # Step 2: Atomic concurrency and idempotency lock
        can_proceed, existing_record = self.idempotency_manager.start_execution(idempotency_key)
        if not can_proceed:
            if existing_record is not None:
                # Idempotent replay: return existing record without triggering payment
                return existing_record
            raise ConcurrencyConflictError(
                f"Concurrent execution in-flight for idempotency key '{idempotency_key}'."
            )

        execution_id = uuid.uuid4()

        # Step 3: Handle Action Semantics
        # A. RETRY_LATER -> DEFERRED
        if request.proposal.action_type == RecoveryActionType.RETRY_LATER:
            record = ExecutionRecord(
                execution_id=execution_id,
                proposal_id=request.proposal.proposal_id,
                target_type=request.target.target_type,
                target_id=request.target.target_id,
                customer_id=request.target.customer_id,
                action_type=request.proposal.action_type,
                amount_minor=request.target.amount_minor,
                currency=request.target.currency,
                status=ExecutionStatus.DEFERRED,
                attempt_number=request.target.target_attempt_count + 1,
                idempotency_key=idempotency_key,
                created_at_iso=now_iso,
                updated_at_iso=now_iso,
            )
            self.idempotency_manager.complete_execution(record)
            self._audit(record, stage="DEFERRED", now_iso=now_iso)
            return record

        # B. Provider-executable action (RETRY_PAYMENT, REQUEST_PAYMENT_METHOD_UPDATE, SUBSCRIPTION_RECOVERY_WORKFLOW)
        attempt_num = request.target.target_attempt_count + 1
        record = ExecutionRecord(
            execution_id=execution_id,
            proposal_id=request.proposal.proposal_id,
            target_type=request.target.target_type,
            target_id=request.target.target_id,
            customer_id=request.target.customer_id,
            action_type=request.proposal.action_type,
            amount_minor=request.target.amount_minor,
            currency=request.target.currency,
            status=ExecutionStatus.EXECUTION_STARTED,
            attempt_number=attempt_num,
            idempotency_key=idempotency_key,
            created_at_iso=now_iso,
            updated_at_iso=now_iso,
        )
        self._audit(record, stage="EXECUTION_STARTED", now_iso=now_iso)

        # Transition: EXECUTION_STARTED -> PROVIDER_REQUESTED
        ExecutionStateMachine.validate_transition(record.status, ExecutionStatus.PROVIDER_REQUESTED)
        record.status = ExecutionStatus.PROVIDER_REQUESTED
        self._audit(record, stage="PROVIDER_REQUESTED", now_iso=now_iso)

        # Dispatch to provider adapter
        prov_req = ProviderRequest(
            idempotency_key=idempotency_key,
            target_type=request.target.target_type,
            target_id=request.target.target_id,
            customer_id=request.target.customer_id,
            amount_minor=request.target.amount_minor,
            currency=request.target.currency,
            action_type=request.proposal.action_type,
            receipt=f"rec_{str(execution_id)[:8]}",
            notes={"proposal_id": str(request.proposal.proposal_id)},
        )

        try:
            prov_resp = await self.provider.execute_recovery(prov_req)
        except Exception as exc:
            # Transport exception treated safely as UNKNOWN_PROVIDER_STATE
            prov_resp = ProviderResponse(
                normalized_status=ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE,
                error_code="TRANSPORT_EXCEPTION",
                error_message=str(exc),
            )

        record.provider_reference = prov_resp.provider_reference
        record.last_error_code = prov_resp.error_code
        record.last_error_message = prov_resp.error_message
        record.updated_at_iso = now_iso

        # Map normalized provider status to execution state
        if prov_resp.normalized_status == ProviderNormalizedStatus.SUCCESS:
            new_status = ExecutionStatus.SUCCEEDED
            stage_name = "PROVIDER_CONFIRMED"
        elif prov_resp.normalized_status == ProviderNormalizedStatus.DECLINED:
            new_status = ExecutionStatus.FAILED
            stage_name = "FAILED"
        elif prov_resp.normalized_status in {
            ProviderNormalizedStatus.TIMEOUT,
            ProviderNormalizedStatus.NETWORK_ERROR,
            ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE,
        }:
            new_status = ExecutionStatus.UNKNOWN_PROVIDER_STATE
            stage_name = "UNKNOWN_PROVIDER_STATE"
        else:
            new_status = ExecutionStatus.FAILED
            stage_name = "FAILED"

        ExecutionStateMachine.validate_transition(record.status, new_status)
        record.status = new_status

        # Finalize and record
        self.idempotency_manager.complete_execution(record)
        self._audit(record, stage=stage_name, now_iso=now_iso, error_code=prov_resp.error_code)
        return record

    def _audit(
        self,
        record: ExecutionRecord,
        stage: str,
        now_iso: str,
        error_code: Optional[str] = None,
    ) -> None:
        """Record an execution lifecycle audit event."""
        self.audit_logger.record_event(
            ExecutionAuditEvent(
                execution_id=record.execution_id,
                proposal_id=record.proposal_id,
                target_type=record.target_type,
                target_id=record.target_id,
                customer_id=record.customer_id,
                action_type=record.action_type.value,
                amount_minor=record.amount_minor,
                currency=record.currency,
                stage=stage,
                status=record.status.value,
                attempt_number=record.attempt_number,
                provider_reference=record.provider_reference,
                idempotency_key=record.idempotency_key,
                timestamp_iso=now_iso,
                error_code=error_code,
            )
        )
