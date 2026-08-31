"""Abstract interface and raw response contract for untrusted LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class RawLLMResponse(BaseModel):
    """Raw, untrusted output returned from an external LLM provider."""

    raw_text: str
    status_code: int = 200
    latency_ms: int = 0
    error_message: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract interface isolating LLM interaction from application logic."""

    provider_name: str
    model_name: str

    @abstractmethod
    async def complete_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float = 30.0,
    ) -> RawLLMResponse:
        """Invoke LLM completion and return raw untrusted response."""
        pass
