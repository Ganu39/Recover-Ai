"""Generic HTTP client provider supporting standard structured JSON LLM endpoints."""

import json
import time
from typing import Optional
import httpx

from agents.diagnosis.providers.base import BaseLLMProvider, RawLLMResponse


class GenericHTTPLLMProvider(BaseLLMProvider):
    """Generic async HTTP adapter for LLM providers exposing standard chat completion endpoints."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        provider_name: str = "generic_http_provider",
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        self.provider_name = provider_name

    async def complete_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float = 30.0,
    ) -> RawLLMResponse:
        start_time = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                latency = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    return RawLLMResponse(
                        raw_text="",
                        status_code=response.status_code,
                        latency_ms=latency,
                        error_message=f"HTTP {response.status_code}: {response.text}",
                    )

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return RawLLMResponse(
                    raw_text=content,
                    status_code=200,
                    latency_ms=latency,
                )

        except httpx.TimeoutException:
            latency = int((time.time() - start_time) * 1000)
            return RawLLMResponse(
                raw_text="",
                status_code=408,
                latency_ms=latency,
                error_message=f"Provider request timed out after {timeout_seconds}s",
            )
        except Exception as exc:
            latency = int((time.time() - start_time) * 1000)
            return RawLLMResponse(
                raw_text="",
                status_code=500,
                latency_ms=latency,
                error_message=f"Provider invocation error: {str(exc)}",
            )
