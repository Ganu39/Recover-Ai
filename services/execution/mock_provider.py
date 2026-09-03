"""Deterministic Mock Payment Provider implementation (Phase 7)."""

import hashlib
import hmac
from typing import Dict, Optional
import uuid

from services.execution.provider import BasePaymentProvider
from services.execution.schemas import (
    ProviderNormalizedStatus,
    ProviderRequest,
    ProviderResponse,
)


class MockPaymentProvider(BasePaymentProvider):
    """Deterministic in-memory mock payment provider for unit testing and benchmarks."""

    def __init__(
        self,
        default_outcome: ProviderNormalizedStatus = ProviderNormalizedStatus.SUCCESS,
    ):
        self.default_outcome = default_outcome
        self.recorded_requests: Dict[str, ProviderRequest] = {}
        self.recorded_responses: Dict[str, ProviderResponse] = {}
        self.status_overrides: Dict[uuid.UUID, ProviderNormalizedStatus] = {}

    def set_target_outcome(self, target_id: uuid.UUID, outcome: ProviderNormalizedStatus) -> None:
        """Set a specific outcome for a target UUID."""
        self.status_overrides[target_id] = outcome

    async def execute_recovery(self, request: ProviderRequest) -> ProviderResponse:
        """Deterministically simulate payment execution."""
        self.recorded_requests[request.idempotency_key] = request

        outcome = self.status_overrides.get(request.target_id, self.default_outcome)
        ref_id = f"pay_mock_{uuid.uuid5(uuid.NAMESPACE_DNS, request.idempotency_key)}"

        if outcome == ProviderNormalizedStatus.SUCCESS:
            resp = ProviderResponse(
                provider_reference=ref_id,
                normalized_status=ProviderNormalizedStatus.SUCCESS,
                raw_details={"order_id": f"order_{ref_id}", "status": "captured"},
            )
        elif outcome == ProviderNormalizedStatus.DECLINED:
            resp = ProviderResponse(
                provider_reference=ref_id,
                normalized_status=ProviderNormalizedStatus.DECLINED,
                error_code="BAD_REQUEST_PAYMENT_DECLINED",
                error_message="Card declined by issuing bank.",
                raw_details={"status": "failed"},
            )
        elif outcome == ProviderNormalizedStatus.TIMEOUT:
            resp = ProviderResponse(
                provider_reference=None,
                normalized_status=ProviderNormalizedStatus.TIMEOUT,
                error_code="GATEWAY_TIMEOUT",
                error_message="Payment provider response timed out.",
            )
        elif outcome == ProviderNormalizedStatus.NETWORK_ERROR:
            resp = ProviderResponse(
                provider_reference=None,
                normalized_status=ProviderNormalizedStatus.NETWORK_ERROR,
                error_code="CONNECTION_REFUSED",
                error_message="Network transport failure during request dispatch.",
            )
        elif outcome == ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE:
            resp = ProviderResponse(
                provider_reference=ref_id,
                normalized_status=ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE,
                error_code="AMBIGUOUS_PROVIDER_STATE",
                error_message="Transaction submitted but final confirmation pending.",
            )
        else:
            resp = ProviderResponse(
                provider_reference=ref_id,
                normalized_status=outcome,
                raw_details={"status": outcome.value},
            )

        if resp.provider_reference:
            self.recorded_responses[resp.provider_reference] = resp
        return resp

    async def query_recovery_status(self, provider_reference: str) -> ProviderResponse:
        """Query status of existing mock transaction."""
        existing = self.recorded_responses.get(provider_reference)
        if existing is not None:
            # Reconcile unknown state to SUCCESS if queried
            if existing.normalized_status == ProviderNormalizedStatus.UNKNOWN_PROVIDER_STATE:
                reconciled = ProviderResponse(
                    provider_reference=provider_reference,
                    normalized_status=ProviderNormalizedStatus.SUCCESS,
                    raw_details={"status": "captured", "reconciled": True},
                )
                self.recorded_responses[provider_reference] = reconciled
                return reconciled
            return existing

        return ProviderResponse(
            provider_reference=provider_reference,
            normalized_status=ProviderNormalizedStatus.VALIDATION_ERROR,
            error_code="TRANSACTION_NOT_FOUND",
            error_message=f"Mock transaction {provider_reference} not found.",
        )

    def verify_webhook_signature(self, body: bytes, signature: str, secret: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        if not secret or not signature:
            return False
        computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)
