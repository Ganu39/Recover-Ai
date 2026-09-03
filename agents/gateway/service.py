"""Deterministic Policy & Safety Gateway Service (Phase 6)."""

import time
from typing import List, Optional, Tuple
import uuid

from agents.decision.schemas import RecoveryActionType, RecoveryDecisionProposal
from agents.gateway.audit import GatewayAuditLogger
from agents.gateway.checks import (
    check_action_allowlist,
    check_failure_category_safety,
    check_financial_integrity,
    check_high_value_and_human_approval,
    check_proposal_identity,
    check_retry_and_chronic_invariants,
    check_schema_and_version,
)
from agents.gateway.idempotency import InMemoryIdempotencyStore
from agents.gateway.kill_switch import GatewayKillSwitch
from agents.gateway.policy import DEFAULT_GATEWAY_POLICY, GatewayPolicy
from agents.gateway.rate_limit import InMemoryRateLimiter
from agents.gateway.schemas import (
    DECISION_VERSION,
    GATEWAY_VERSION,
    POLICY_VERSION,
    GatewayAuditRecord,
    GatewayConfig,
    GatewayDecision,
    GatewayDecisionResult,
    GatewayReasonCode,
    GatewayTargetContext,
    HumanApprovalRecord,
)


class DeterministicSafetyGateway:
    """The final deterministic safety boundary before downstream payment execution.
    
    Zero Razorpay imports, zero external HTTP calls, zero payment execution side effects.
    Evaluates proposals and produces an auditable, fail-closed authorization decision.
    """

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
        policy: Optional[GatewayPolicy] = None,
        idempotency_store: Optional[InMemoryIdempotencyStore] = None,
        rate_limiter: Optional[InMemoryRateLimiter] = None,
        kill_switch: Optional[GatewayKillSwitch] = None,
        audit_logger: Optional[GatewayAuditLogger] = None,
    ):
        self.config = config or GatewayConfig()
        self.policy = policy or DEFAULT_GATEWAY_POLICY
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()
        self.rate_limiter = rate_limiter or InMemoryRateLimiter(
            max_per_window=self.config.rate_limit_per_target_window,
            window_seconds=self.config.window_seconds,
        )
        self.kill_switch = kill_switch or GatewayKillSwitch.from_config(self.config)
        self.audit_logger = audit_logger or GatewayAuditLogger()

    def evaluate_proposal(
        self,
        proposal: RecoveryDecisionProposal,
        target: GatewayTargetContext,
        approval: Optional[HumanApprovalRecord] = None,
        now_epoch: Optional[float] = None,
    ) -> GatewayDecisionResult:
        """Evaluate a single proposal against the 12-stage deterministic safety pipeline."""
        if now_epoch is None:
            now_epoch = time.time()

        audit_reference = uuid.uuid4()
        evaluated_epoch_ms = int(now_epoch * 1000)

        checks_evaluated: List[str] = []
        checks_passed: List[str] = []
        blocking_conditions: List[str] = []

        try:
            # -------------------------------------------------------------
            # STAGE 1: KILL SWITCH (FAIL-SAFE GLOBAL GATE)
            # -------------------------------------------------------------
            checks_evaluated.append("kill_switch_check")
            if self.kill_switch.is_active():
                blocking_conditions.append("Safety kill switch is active: all execution authorizations suspended.")
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.KILL_SWITCH_ACTIVE,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason="Safety kill switch engaged; execution layer eligibility prohibited.",
                    reason_code=GatewayReasonCode.KILL_SWITCH_ACTIVE,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_audit(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("kill_switch_check")

            # -------------------------------------------------------------
            # STAGE 2: SCHEMA & VERSION VALIDATION
            # -------------------------------------------------------------
            checks_evaluated.append("schema_and_version_validation")
            ok, reason_code, reason_msg = check_schema_and_version(proposal, target, self.config)
            if not ok:
                blocking_conditions.append(reason_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.INVALID_PROPOSAL,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.BLOCK_SCHEMA_VALIDATION_FAILED,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_audit(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("schema_and_version_validation")

            # -------------------------------------------------------------
            # STAGE 3: PROPOSAL IDENTITY VALIDATION (UUID5 INDEPENDENT RECOMPUTATION)
            # -------------------------------------------------------------
            checks_evaluated.append("proposal_identity_validation")
            ok, reason_code, reason_msg = check_proposal_identity(proposal, target)
            if not ok:
                blocking_conditions.append(reason_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.INVALID_PROPOSAL,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.BLOCK_PROPOSAL_IDENTITY_MISMATCH,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_audit(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("proposal_identity_validation")

            # -------------------------------------------------------------
            # STAGE 4: FINANCIAL INTEGRITY VALIDATION (INTEGER MINOR UNITS)
            # -------------------------------------------------------------
            checks_evaluated.append("financial_integrity_validation")
            ok, reason_code, reason_msg = check_financial_integrity(proposal, target)
            if not ok:
                blocking_conditions.append(reason_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.INVALID_PROPOSAL,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.BLOCK_AMOUNT_MISMATCH,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_audit(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("financial_integrity_validation")

            # -------------------------------------------------------------
            # STAGE 5: IDEMPOTENCY & REPLAY PROTECTION
            # -------------------------------------------------------------
            checks_evaluated.append("idempotency_replay_check")
            action_str = (
                proposal.action_type.value
                if hasattr(proposal.action_type, "value")
                else str(proposal.action_type)
            )

            existing = self.idempotency_store.get_existing_decision(
                proposal_id=proposal.proposal_id,
                gateway_version=self.config.gateway_version,
                policy_version=self.config.policy_version,
            )
            if existing is not None:
                # If existing decision exists for this proposal_id, check if action or amount was tampered/conflicted
                stored_entry = self.idempotency_store.get_stored_target_entry(
                    target.target_type, target.target_id
                )
                if stored_entry is not None:
                    _, stored_action, stored_amt, _ = stored_entry
                    if stored_action != action_str or stored_amt != proposal.amount_minor:
                        conflict_msg = (
                            f"Target {target.target_type}:{target.target_id} already has a recorded decision "
                            f"with action '{stored_action}' and amount {stored_amt} paise. "
                            f"Conflicting proposal with action '{action_str}' and amount {proposal.amount_minor} paise rejected."
                        )
                        blocking_conditions.append(conflict_msg)
                        result = GatewayDecisionResult(
                            gateway_decision=GatewayDecision.BLOCKED,
                            proposal_id=proposal.proposal_id,
                            target_type=target.target_type,
                            target_id=target.target_id,
                            decision_reason=conflict_msg,
                            reason_code=GatewayReasonCode.BLOCK_CONFLICTING_PROPOSAL_FOR_TARGET,
                            policy_version=self.config.policy_version,
                            gateway_version=self.config.gateway_version,
                            decision_version=self.config.decision_version,
                            checks_evaluated=checks_evaluated,
                            checks_passed=checks_passed,
                            blocking_conditions=blocking_conditions,
                            audit_reference=audit_reference,
                            eligible_for_execution_layer=False,
                            is_replay=False,
                        )
                        self._record_audit(result, proposal, target, evaluated_epoch_ms)
                        return result

                # Return previously recorded outcome without re-authorizing
                replay_reason_code = (
                    GatewayReasonCode.IDEMPOTENT_REPLAY_APPROVED
                    if existing.gateway_decision == GatewayDecision.APPROVED
                    else GatewayReasonCode.IDEMPOTENT_REPLAY_BLOCKED
                )
                replay_result = GatewayDecisionResult(
                    gateway_decision=existing.gateway_decision,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=f"Idempotent replay: returning cached decision ({existing.gateway_decision.value})",
                    reason_code=replay_reason_code,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=existing.blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=existing.eligible_for_execution_layer,
                    is_replay=True,
                )
                self._record_audit(replay_result, proposal, target, evaluated_epoch_ms)
                return replay_result

            # Check for conflicting proposal on same target across distinct proposals
            conflict = self.idempotency_store.check_target_conflict(
                target_type=target.target_type,
                target_id=target.target_id,
                proposal_id=proposal.proposal_id,
                action_type=action_str,
                amount_minor=proposal.amount_minor,
            )
            if conflict is not None:
                conflict_code, conflict_msg = conflict
                blocking_conditions.append(conflict_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.BLOCKED,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=conflict_msg,
                    reason_code=conflict_code,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_audit(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("idempotency_replay_check")

            # -------------------------------------------------------------
            # STAGE 6: EXECUTABLE ACTION ALLOWLIST VALIDATION
            # -------------------------------------------------------------
            checks_evaluated.append("action_allowlist_validation")
            ok, reason_code, reason_msg = check_action_allowlist(proposal)
            if not ok:
                blocking_conditions.append(reason_msg)
                decision = (
                    GatewayDecision.REQUIRES_REVIEW
                    if proposal.action_type == RecoveryActionType.HUMAN_REVIEW
                    else GatewayDecision.BLOCKED
                )
                result = GatewayDecisionResult(
                    gateway_decision=decision,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.BLOCK_NON_EXECUTABLE_ACTION,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_and_store(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("action_allowlist_validation")

            # -------------------------------------------------------------
            # STAGE 7: RETRY & CHRONIC FAILURE INVARIANTS (DEFENSE-IN-DEPTH)
            # -------------------------------------------------------------
            checks_evaluated.append("retry_and_chronic_invariants")
            ok, reason_code, reason_msg = check_retry_and_chronic_invariants(proposal, target, self.policy)
            if not ok:
                blocking_conditions.append(reason_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.BLOCKED,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.BLOCK_RETRY_LIMIT_EXCEEDED,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_and_store(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("retry_and_chronic_invariants")

            # -------------------------------------------------------------
            # STAGE 8: FAILURE CATEGORY SAFETY CHECK
            # -------------------------------------------------------------
            checks_evaluated.append("failure_category_safety")
            ok, reason_code, reason_msg = check_failure_category_safety(proposal, target, self.policy)
            if not ok:
                blocking_conditions.append(reason_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.BLOCKED,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.BLOCK_UNRESOLVED_HARD_DECLINE,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_and_store(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("failure_category_safety")

            # -------------------------------------------------------------
            # STAGE 9: HIGH-VALUE & HUMAN APPROVAL CHECK
            # -------------------------------------------------------------
            checks_evaluated.append("high_value_and_human_approval")
            ok, reason_code, reason_msg = check_high_value_and_human_approval(
                proposal, target, self.config, approval
            )
            if not ok:
                blocking_conditions.append(reason_msg)
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.REQUIRES_REVIEW,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason=reason_msg,
                    reason_code=reason_code or GatewayReasonCode.MISSING_HUMAN_APPROVAL,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_and_store(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("high_value_and_human_approval")

            # -------------------------------------------------------------
            # STAGE 10: RATE LIMIT CHECK
            # -------------------------------------------------------------
            checks_evaluated.append("rate_limit_check")
            if self.rate_limiter.is_rate_limited(
                target.target_type, target.target_id, target.customer_id, now_epoch=now_epoch
            ):
                blocking_conditions.append("Rate limit threshold exceeded for target/customer window.")
                result = GatewayDecisionResult(
                    gateway_decision=GatewayDecision.RATE_LIMITED,
                    proposal_id=proposal.proposal_id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                    decision_reason="Safety rate limit exceeded; execution request throttled.",
                    reason_code=GatewayReasonCode.RATE_LIMIT_EXCEEDED,
                    policy_version=self.config.policy_version,
                    gateway_version=self.config.gateway_version,
                    decision_version=self.config.decision_version,
                    checks_evaluated=checks_evaluated,
                    checks_passed=checks_passed,
                    blocking_conditions=blocking_conditions,
                    audit_reference=audit_reference,
                    eligible_for_execution_layer=False,
                    is_replay=False,
                )
                self._record_audit(result, proposal, target, evaluated_epoch_ms)
                return result

            checks_passed.append("rate_limit_check")

            # -------------------------------------------------------------
            # STAGE 11 & 12: FINAL GATEWAY AUTHORIZATION
            # -------------------------------------------------------------
            self.rate_limiter.record_attempt(
                target.target_type, target.target_id, target.customer_id, now_epoch=now_epoch
            )

            result = GatewayDecisionResult(
                gateway_decision=GatewayDecision.APPROVED,
                proposal_id=proposal.proposal_id,
                target_type=target.target_type,
                target_id=target.target_id,
                decision_reason="Proposal passed all deterministic policy and safety invariants.",
                reason_code=GatewayReasonCode.APPROVED_FOR_EXECUTION_LAYER,
                policy_version=self.config.policy_version,
                gateway_version=self.config.gateway_version,
                decision_version=self.config.decision_version,
                checks_evaluated=checks_evaluated,
                checks_passed=checks_passed,
                blocking_conditions=[],
                audit_reference=audit_reference,
                eligible_for_execution_layer=True,
                is_replay=False,
            )
            self._record_and_store(result, proposal, target, evaluated_epoch_ms)
            return result

        except Exception as exc:
            # Absolute fail-closed error handling
            error_reason = f"Gateway unexpected internal failure: {type(exc).__name__}"
            fail_closed_result = GatewayDecisionResult(
                gateway_decision=GatewayDecision.INVALID_PROPOSAL,
                proposal_id=proposal.proposal_id,
                target_type=target.target_type,
                target_id=target.target_id,
                decision_reason=error_reason,
                reason_code=GatewayReasonCode.GATEWAY_CONFIGURATION_ERROR,
                policy_version=self.config.policy_version,
                gateway_version=self.config.gateway_version,
                decision_version=self.config.decision_version,
                checks_evaluated=checks_evaluated,
                checks_passed=checks_passed,
                blocking_conditions=[error_reason],
                audit_reference=audit_reference,
                eligible_for_execution_layer=False,
                is_replay=False,
            )
            self._record_audit(fail_closed_result, proposal, target, evaluated_epoch_ms)
            return fail_closed_result

    def _record_audit(
        self,
        result: GatewayDecisionResult,
        proposal: RecoveryDecisionProposal,
        target: GatewayTargetContext,
        evaluated_epoch_ms: int,
    ) -> None:
        """Internal helper to construct and append an immutable audit record."""
        action_str = (
            proposal.action_type.value
            if hasattr(proposal.action_type, "value")
            else str(proposal.action_type)
        )
        audit_rec = GatewayAuditRecord(
            audit_reference=result.audit_reference,
            evaluated_at_epoch_ms=evaluated_epoch_ms,
            proposal_id=result.proposal_id,
            target_type=result.target_type,
            target_id=result.target_id,
            customer_id=target.customer_id,
            amount_minor=target.amount_minor,
            currency=target.currency,
            action_type=action_str,
            gateway_decision=result.gateway_decision,
            reason_code=result.reason_code,
            decision_reason=result.decision_reason,
            policy_version=result.policy_version,
            gateway_version=result.gateway_version,
            decision_version=result.decision_version,
            checks_evaluated=result.checks_evaluated,
            checks_passed=result.checks_passed,
            blocking_conditions=result.blocking_conditions,
            eligible_for_execution_layer=result.eligible_for_execution_layer,
            is_replay=result.is_replay,
        )
        self.audit_logger.record(audit_rec)

    def _record_and_store(
        self,
        result: GatewayDecisionResult,
        proposal: RecoveryDecisionProposal,
        target: GatewayTargetContext,
        evaluated_epoch_ms: int,
    ) -> None:
        """Helper to record in audit logger AND persist in idempotency registry."""
        self._record_audit(result, proposal, target, evaluated_epoch_ms)
        action_str = (
            proposal.action_type.value
            if hasattr(proposal.action_type, "value")
            else str(proposal.action_type)
        )
        self.idempotency_store.record_decision(
            proposal_id=proposal.proposal_id,
            target_type=target.target_type,
            target_id=target.target_id,
            action_type=action_str,
            amount_minor=target.amount_minor,
            gateway_version=self.config.gateway_version,
            policy_version=self.config.policy_version,
            decision_result=result,
        )

    def evaluate_batch(
        self,
        pairs: List[Tuple[RecoveryDecisionProposal, GatewayTargetContext, Optional[HumanApprovalRecord]]],
        now_epoch: Optional[float] = None,
    ) -> List[GatewayDecisionResult]:
        """Deterministically evaluate a batch of (proposal, target, approval) tuples."""
        return [
            self.evaluate_proposal(prop, tgt, app, now_epoch=now_epoch)
            for prop, tgt, app in pairs
        ]
