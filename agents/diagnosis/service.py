"""DiagnosisAgent orchestrating prompt rendering, untrusted provider invocation, schema validation, and fallback."""

import json
from pathlib import Path
from typing import List, Optional
import uuid

from agents.diagnosis.providers.base import BaseLLMProvider
from agents.diagnosis.schemas import (
    AIDiagnosisInputContext,
    AIDiagnosisPayload,
    AIDiagnosisResult,
    DiagnosisCategory,
    DiagnosisStatus,
    QualitativeConfidence,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class DiagnosisAgent:
    """Read-only AI reasoning agent for root-cause diagnosis of revenue-recovery opportunities."""

    def __init__(self, provider: BaseLLMProvider, prompt_version: str = "v1"):
        self.provider = provider
        self.prompt_version = prompt_version
        self._load_prompts()

    def _load_prompts(self):
        """Load versioned immutable prompt templates from disk."""
        version_dir = PROMPTS_DIR / self.prompt_version
        system_path = version_dir / "system_prompt.md"
        user_path = version_dir / "user_template.md"

        if not system_path.exists() or not user_path.exists():
            raise FileNotFoundError(f"Prompt templates not found for version {self.prompt_version} in {version_dir}")

        self.system_prompt = system_path.read_text(encoding="utf-8")
        self.user_template = user_path.read_text(encoding="utf-8")

    def _render_user_prompt(self, ctx: AIDiagnosisInputContext) -> str:
        """Deterministically render user prompt template from input context."""
        attempts_lines = []
        if ctx.attempts:
            for att in ctx.attempts:
                attempts_lines.append(
                    f"  - Attempt {att.attempt_number}: {att.failure_code or 'None'} "
                    f"({att.failure_reason or 'No reason provided'}) [offset: {att.attempt_offset_seconds}s]"
                )
        else:
            attempts_lines.append("  - (No individual attempt records)")

        return self.user_template.format(
            target_type=ctx.target_type,
            masked_target_id=ctx.masked_target_id,
            masked_customer_id=ctx.masked_customer_id,
            amount_display=ctx.amount_display,
            amount_minor=ctx.amount_minor,
            currency=ctx.currency,
            customer_tenure_days=ctx.customer_tenure_days,
            customer_history_count=ctx.customer_history_count,
            customer_success_count=ctx.customer_success_count,
            customer_historical_success_rate_pct=ctx.customer_historical_success_rate_pct,
            subscription_status=ctx.subscription_status or "N/A",
            attempts_formatted="\n".join(attempts_lines),
        )

    def _build_fallback_result(
        self,
        ctx: AIDiagnosisInputContext,
        status: DiagnosisStatus,
        latency_ms: int,
        error_message: str,
    ) -> AIDiagnosisResult:
        """Construct deterministic fallback result for provider failures or validation errors."""
        return AIDiagnosisResult(
            prompt_version=self.prompt_version,
            provider_name=self.provider.provider_name,
            model_name=self.provider.model_name,
            latency_ms=latency_ms,
            status=status,
            case_id=ctx.case_id,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
            amount_minor=ctx.amount_minor,
            currency=ctx.currency,
            diagnosis_category=DiagnosisCategory.INSUFFICIENT_DATA,
            diagnosis_summary="AI diagnosis unavailable due to provider or validation failure.",
            observed_facts=[],
            evidence_reasoning=[],
            missing_information=["AI provider execution was incomplete or unparseable"],
            ai_recoverability_assessment=None,  # Not a valid diagnosis decision
            confidence=QualitativeConfidence.LOW,
            ai_recoverability_reason="Diagnosis fallback engaged.",
            error_message=error_message,
        )

    async def diagnose(self, ctx: AIDiagnosisInputContext, timeout_seconds: float = 30.0) -> AIDiagnosisResult:
        """Execute single root-cause diagnosis over observable context."""
        user_prompt = self._render_user_prompt(ctx)

        # 1. Invoke untrusted provider
        raw_resp = await self.provider.complete_prompt(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )

        # 2. Check HTTP / Provider execution status
        if raw_resp.status_code == 408:
            return self._build_fallback_result(
                ctx,
                DiagnosisStatus.TIMEOUT,
                raw_resp.latency_ms,
                raw_resp.error_message or "Request timed out",
            )
        elif raw_resp.status_code != 200:
            return self._build_fallback_result(
                ctx,
                DiagnosisStatus.PROVIDER_ERROR,
                raw_resp.latency_ms,
                raw_resp.error_message or f"HTTP {raw_resp.status_code}",
            )

        # 3. Parse JSON
        try:
            parsed_json = json.loads(raw_resp.raw_text)
        except Exception as json_err:
            return self._build_fallback_result(
                ctx,
                DiagnosisStatus.VALIDATION_ERROR,
                raw_resp.latency_ms,
                f"Malformed JSON response: {str(json_err)}",
            )

        # 4. Strict Schema Validation via Pydantic
        try:
            payload = AIDiagnosisPayload.model_validate(parsed_json)
        except Exception as val_err:
            return self._build_fallback_result(
                ctx,
                DiagnosisStatus.VALIDATION_ERROR,
                raw_resp.latency_ms,
                f"Schema validation failed: {str(val_err)}",
            )

        # 5. Build Trusted Application Domain Result
        return AIDiagnosisResult(
            prompt_version=self.prompt_version,
            provider_name=self.provider.provider_name,
            model_name=self.provider.model_name,
            latency_ms=raw_resp.latency_ms,
            status=DiagnosisStatus.SUCCESS,
            case_id=ctx.case_id,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
            amount_minor=ctx.amount_minor,
            currency=ctx.currency,
            diagnosis_category=payload.diagnosis_category,
            diagnosis_summary=payload.diagnosis_summary,
            observed_facts=payload.observed_facts,
            evidence_reasoning=payload.evidence_reasoning,
            missing_information=payload.missing_information,
            ai_recoverability_assessment=payload.ai_recoverability_assessment,
            confidence=payload.confidence,
            ai_recoverability_reason=payload.ai_recoverability_reason,
            error_message=None,
        )

    async def diagnose_batch(
        self, contexts: List[AIDiagnosisInputContext], timeout_seconds: float = 30.0
    ) -> List[AIDiagnosisResult]:
        """Execute diagnosis over a collection of contexts."""
        results = []
        for ctx in contexts:
            res = await self.diagnose(ctx, timeout_seconds=timeout_seconds)
            results.append(res)
        return results
