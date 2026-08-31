"""Deterministic mock LLM provider for unit tests, offline validation, and failure-path testing."""

import json
import time
from typing import Optional

from agents.diagnosis.providers.base import BaseLLMProvider, RawLLMResponse
from agents.diagnosis.schemas import DiagnosisCategory, QualitativeConfidence


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider simulating structured LLM output for testing without live API keys."""

    def __init__(
        self,
        provider_name: str = "mock_diagnostic_provider",
        model_name: str = "mock-simulated-v1",
        injected_fault: Optional[str] = None,
    ):
        self.provider_name = provider_name
        self.model_name = model_name
        self.injected_fault = injected_fault

    async def complete_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float = 30.0,
    ) -> RawLLMResponse:
        start_time = time.time()

        # Handle simulated error conditions
        if self.injected_fault == "timeout":
            return RawLLMResponse(
                raw_text="",
                status_code=408,
                latency_ms=int(timeout_seconds * 1000),
                error_message="Request timed out after timeout_seconds",
            )
        elif self.injected_fault == "http_500":
            return RawLLMResponse(
                raw_text="",
                status_code=500,
                latency_ms=15,
                error_message="HTTP 500: Internal Server Error from upstream provider",
            )
        elif self.injected_fault == "malformed_json":
            return RawLLMResponse(
                raw_text="NOT_VALID_JSON: { unquoted_key: 123 ",
                status_code=200,
                latency_ms=25,
            )
        elif self.injected_fault == "schema_violation":
            return RawLLMResponse(
                raw_text=json.dumps({"invalid_root": "missing_required_fields"}),
                status_code=200,
                latency_ms=20,
            )

        # Deterministic domain deduction based on prompt contents
        if "subscription_status: past_due" in user_prompt.lower() or "target type: subscription" in user_prompt.lower():
            category = DiagnosisCategory.SUBSCRIPTION_BILLING_ISSUE
            summary = "Recurring subscription failed during scheduled billing cycle."
            facts = ["Target is a recurring subscription", "Subscription status is past_due"]
            evidence = [
                {
                    "fact": "Subscription is marked past_due",
                    "source_field": "subscription_status",
                    "inference": "Recurring mandate execution failed on scheduled interval.",
                }
            ]
            recoverable = True
            confidence = QualitativeConfidence.HIGH
            rec_reason = "Recurring billing glitches on active subscriptions are highly recoverable with retry or updated payment method."

        elif "attempt number: 3" in user_prompt.lower() or "attempts: 3" in user_prompt.lower() or "attempts: 4" in user_prompt.lower():
            category = DiagnosisCategory.PERSISTENT_ISSUER_DECLINE
            summary = "Multiple consecutive attempts declined by card issuer."
            facts = ["3 or more failed payment attempts recorded"]
            evidence = [
                {
                    "fact": "Repeated failed attempts on current payment",
                    "source_field": "attempts",
                    "inference": "Issuer persistently declining transaction.",
                }
            ]
            recoverable = False
            confidence = QualitativeConfidence.HIGH
            rec_reason = "Exhausted attempt threshold indicates persistent authorization refusal."

        elif "temporary_failure" in user_prompt.lower():
            category = DiagnosisCategory.TRANSIENT_SYSTEM_ERROR
            summary = "Temporary gateway or network timeout during authorization switch."
            facts = ["Gateway returned temporary_failure decline code"]
            evidence = [
                {
                    "fact": "Failure code indicates temporary network error",
                    "source_field": "attempts[0].failure_code",
                    "inference": "Transient error unrelated to customer creditworthiness.",
                }
            ]
            recoverable = True
            confidence = QualitativeConfidence.HIGH
            rec_reason = "Transient network errors on proven accounts have high recovery viability."

        elif "insufficient_funds" in user_prompt.lower():
            category = DiagnosisCategory.BALANCE_OR_LIMIT_DEFICIT
            summary = "Authorization declined due to temporary balance deficit."
            facts = ["Gateway returned insufficient_funds decline code"]
            evidence = [
                {
                    "fact": "Decline code indicates balance deficit",
                    "source_field": "attempts[0].failure_code",
                    "inference": "Account balance was insufficient at moment of charge.",
                }
            ]
            recoverable = True
            confidence = QualitativeConfidence.MEDIUM
            rec_reason = "Balance deficits can be recovered via smart retry scheduling or alternate payment links."

        elif "customer history: 0 successful / 0 total" in user_prompt.lower() or "customer history: 0 successful / 1 total" in user_prompt.lower():
            category = DiagnosisCategory.FIRST_TIME_USER_DROP
            summary = "First-time customer checkout drop-off."
            facts = ["New customer with zero or one prior transaction history"]
            evidence = [
                {
                    "fact": "Customer has <= 1 prior payments",
                    "source_field": "customer_history_count",
                    "inference": "Customer encountering initial checkout friction.",
                }
            ]
            recoverable = True
            confidence = QualitativeConfidence.MEDIUM
            rec_reason = "New customer drop-offs are recoverable via automated checkout reminders."

        else:
            category = DiagnosisCategory.INSUFFICIENT_DATA
            summary = "Unclear transaction signals prevent definitive classification."
            facts = ["Ambiguous decline signals without clear historical pattern"]
            evidence = []
            recoverable = False
            confidence = QualitativeConfidence.LOW
            rec_reason = "Insufficient diagnostic signals to assess recovery viability."

        response_dict = {
            "diagnosis_category": category.value,
            "diagnosis_summary": summary,
            "observed_facts": facts,
            "evidence_reasoning": evidence,
            "missing_information": [],
            "ai_recoverability_assessment": recoverable,
            "confidence": confidence.value,
            "ai_recoverability_reason": rec_reason,
        }

        latency = int((time.time() - start_time) * 1000)
        return RawLLMResponse(
            raw_text=json.dumps(response_dict),
            status_code=200,
            latency_ms=latency,
        )
