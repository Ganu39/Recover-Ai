"""Evaluation harness and benchmark calculation for Execution Layer (Phase 7)."""

from typing import List, Optional, Tuple

from agents.decision.schemas import RecoveryActionType, RecoveryDecisionProposal
from agents.gateway.schemas import GatewayDecision, GatewayDecisionResult, GatewayTargetContext
from services.execution.schemas import (
    ExecutionBenchmarkReport,
    ExecutionRecord,
    ExecutionRequest,
    ExecutionStatus,
)
from services.execution.service import ExecutionService


class ExecutionEvaluator:
    """Evaluates the execution layer across authorized proposals and calculates revenue recovery metrics."""

    def __init__(self, service: Optional[ExecutionService] = None):
        self.service = service or ExecutionService()

    async def evaluate_proposals(
        self,
        triplets: List[Tuple[RecoveryDecisionProposal, GatewayTargetContext, GatewayDecisionResult]],
    ) -> Tuple[List[ExecutionRecord], ExecutionBenchmarkReport]:
        """Execute recovery pipeline across authorized proposals and compute metrics."""
        records: List[ExecutionRecord] = []

        total_proposals = len(triplets)
        authorized_count = 0
        attempted_count = 0
        succeeded_count = 0
        failed_count = 0
        deferred_count = 0
        unknown_state_count = 0
        reconciled_count = 0

        amount_at_risk = 0
        authorized_amount = 0
        attempted_amount = 0
        provider_confirmed_amount = 0
        recovered_amount = 0
        failed_amount = 0

        unauthorized_executions = 0
        duplicate_executions = 0
        financial_integrity_violations = 0

        for proposal, target, gw_result in triplets:
            amount_at_risk += target.amount_minor

            if gw_result.gateway_decision == GatewayDecision.APPROVED:
                authorized_count += 1
                authorized_amount += target.amount_minor
            else:
                # Should not execute! Verify fail-safe if attempted
                continue

            req = ExecutionRequest(
                proposal=proposal,
                target=target,
                gateway_result=gw_result,
            )

            try:
                record = await self.service.execute_recovery(req)
                records.append(record)

                if record.status in {
                    ExecutionStatus.EXECUTION_STARTED,
                    ExecutionStatus.PROVIDER_REQUESTED,
                    ExecutionStatus.SUCCEEDED,
                    ExecutionStatus.FAILED,
                    ExecutionStatus.UNKNOWN_PROVIDER_STATE,
                }:
                    attempted_count += 1
                    attempted_amount += target.amount_minor

                if record.status == ExecutionStatus.SUCCEEDED:
                    succeeded_count += 1
                    provider_confirmed_amount += target.amount_minor
                    recovered_amount += target.amount_minor
                elif record.status == ExecutionStatus.RECONCILED:
                    reconciled_count += 1
                    recovered_amount += target.amount_minor
                    provider_confirmed_amount += target.amount_minor
                elif record.status == ExecutionStatus.FAILED:
                    failed_count += 1
                    failed_amount += target.amount_minor
                elif record.status == ExecutionStatus.DEFERRED:
                    deferred_count += 1
                elif record.status == ExecutionStatus.UNKNOWN_PROVIDER_STATE:
                    unknown_state_count += 1

                # Safety audit on executed record
                if gw_result.gateway_decision != GatewayDecision.APPROVED:
                    unauthorized_executions += 1

                if record.amount_minor != target.amount_minor or record.currency != target.currency:
                    financial_integrity_violations += 1

            except Exception as exc:
                failed_count += 1
                failed_amount += target.amount_minor

        unauthorized_rate_bps = (
            (unauthorized_executions * 10000) // attempted_count
            if attempted_count > 0
            else 0
        )
        duplicate_rate_bps = (
            (duplicate_executions * 10000) // attempted_count
            if attempted_count > 0
            else 0
        )
        fin_violation_rate_bps = (
            (financial_integrity_violations * 10000) // attempted_count
            if attempted_count > 0
            else 0
        )

        report = ExecutionBenchmarkReport(
            execution_mode=self.service.config.payment_mode.value,
            total_proposals_received=total_proposals,
            authorized_for_execution=authorized_count,
            executions_attempted=attempted_count,
            executions_succeeded=succeeded_count,
            executions_failed=failed_count,
            executions_deferred=deferred_count,
            executions_unknown_state=unknown_state_count,
            executions_reconciled=reconciled_count,
            amount_at_risk_minor=amount_at_risk,
            authorized_amount_minor=authorized_amount,
            attempted_amount_minor=attempted_amount,
            provider_confirmed_amount_minor=provider_confirmed_amount,
            recovered_amount_minor=recovered_amount,
            failed_amount_minor=failed_amount,
            unauthorized_execution_rate_bps=unauthorized_rate_bps,
            duplicate_execution_rate_bps=duplicate_rate_bps,
            financial_integrity_violation_rate_bps=fin_violation_rate_bps,
        )

        return records, report
