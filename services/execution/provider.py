"""Payment Provider abstract base class (Phase 7)."""

from abc import ABC, abstractmethod

from services.execution.schemas import ProviderRequest, ProviderResponse


class BasePaymentProvider(ABC):
    """Abstract interface for payment gateway provider adapters."""

    @abstractmethod
    async def execute_recovery(self, request: ProviderRequest) -> ProviderResponse:
        """Execute a payment recovery attempt with the external gateway."""
        pass

    @abstractmethod
    async def query_recovery_status(self, provider_reference: str) -> ProviderResponse:
        """Query the authoritative status of an existing provider payment/order."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, signature: str, secret: str) -> bool:
        """Cryptographically verify the authenticity of an incoming provider webhook."""
        pass
