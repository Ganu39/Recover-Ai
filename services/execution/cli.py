"""CLI benchmark runner for Phase 7 Bounded Recovery Execution Layer."""

import argparse
import asyncio
import json
import time
from typing import List, Optional, Tuple

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from agents.decision.policy import DEFAULT_RECOVERY_POLICY
from agents.decision.schemas import DecisionInputContext, RecoveryDecisionProposal
from agents.decision.service import RecoveryDecisionAgent
from agents.diagnosis.context_builder import AIDiagnosisContextBuilder
from agents.diagnosis.providers.mock import MockLLMProvider
from agents.diagnosis.service import DiagnosisAgent
from agents.gateway.evaluator import GatewayEvaluator
from agents.gateway.schemas import GatewayDecisionResult, GatewayTargetContext
from services.execution.evaluator import ExecutionEvaluator
from services.execution.mock_provider import MockPaymentProvider
from services.execution.schemas import ExecutionConfig, PaymentExecutionMode
from services.execution.service import ExecutionService
from services.risk_engine.extractor import ObservableFeatureExtractor


async def run_execution_benchmark(args):
    config = GeneratorConfig(seed=args.seed, num_customers=args.customers, num_payments=args.payments)
    print(f"Generating synthetic dataset (Seed: {config.seed}, Customers: {config.num_customers}, Payments: {config.num_payments})...")
    dataset = SyntheticDataGenerator(config).generate()

    print(f"Extracting contexts & generating Phase 4 AI diagnoses for {len(dataset.observable.recovery_cases)} cases...")
    obs_contexts = ObservableFeatureExtractor.extract_from_dataset(dataset.observable)
    ai_contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)

    diagnosis_agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
    ai_diagnoses = await diagnosis_agent.diagnose_batch(ai_contexts)
    ai_diag_map = {d.case_id: d for d in ai_diagnoses if d.case_id}

    print("Synthesizing Phase 5 Decision Proposals & Phase 6 Gateway Authorizations...")
    decision_contexts: List[DecisionInputContext] = []
    target_contexts: List[GatewayTargetContext] = []
    for ctx in obs_contexts:
        ai_diag = ai_diag_map.get(ctx.case_id)
        d_ctx = DecisionInputContext(
            case_id=ctx.case_id,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
            customer_id=ctx.customer_id,
            amount_minor=ctx.amount_at_risk_minor,
            currency=ctx.currency,
            amount_display=f"₹{ctx.amount_at_risk_minor / 100:,.2f}",
            customer_history_count=ctx.customer_history_count,
            customer_success_count=ctx.customer_success_count,
            customer_success_rate_bps=ctx.customer_success_rate_bps,
            target_attempt_count=ctx.target_attempt_count,
            latest_failure_code=ctx.latest_failure_code,
            subscription_status=ctx.subscription_status,
            ai_diagnosis=ai_diag,
        )
        decision_contexts.append(d_ctx)

        tgt_ctx = GatewayTargetContext(
            case_id=ctx.case_id,
            target_type=ctx.target_type,
            target_id=ctx.target_id,
            customer_id=ctx.customer_id,
            amount_minor=ctx.amount_at_risk_minor,
            currency=ctx.currency,
            amount_display=f"₹{ctx.amount_at_risk_minor / 100:,.2f}",
            customer_history_count=ctx.customer_history_count,
            customer_success_count=ctx.customer_success_count,
            customer_success_rate_bps=ctx.customer_success_rate_bps,
            target_attempt_count=ctx.target_attempt_count,
            latest_failure_code=ctx.latest_failure_code,
            subscription_status=ctx.subscription_status,
        )
        target_contexts.append(tgt_ctx)

    decision_agent = RecoveryDecisionAgent(policy=DEFAULT_RECOVERY_POLICY)
    proposals: List[RecoveryDecisionProposal] = decision_agent.evaluate_batch(decision_contexts)

    gateway_evaluator = GatewayEvaluator()
    gateway_triplets = [(p, t, None) for p, t in zip(proposals, target_contexts)]
    gw_results, gw_report = gateway_evaluator.evaluate(gateway_triplets)

    print(f"Executing Phase 7 Bounded Execution Layer across {len(proposals)} items...")
    exec_start = time.time()
    mock_provider = MockPaymentProvider()
    exec_config = ExecutionConfig(payment_mode=PaymentExecutionMode.SIMULATION)
    exec_service = ExecutionService(config=exec_config, provider=mock_provider)
    exec_evaluator = ExecutionEvaluator(service=exec_service)

    exec_triplets = [(p, t, r) for p, t, r in zip(proposals, target_contexts, gw_results)]
    records, report = await exec_evaluator.evaluate_proposals(exec_triplets)
    exec_time = time.time() - exec_start

    print("\n========================================================")
    print("  RECOVERAI — PHASE 7 EXECUTION BENCHMARK SCORECARD")
    print("========================================================")
    print(f"Execution Mode:                 {report.execution_mode}")
    print(f"Dataset Seed:                   {args.seed}")
    print(f"Total Proposals Received:       {report.total_proposals_received}")
    print(f"Authorized by Gateway (Phase 6): {report.authorized_for_execution}")
    print(f"Executions Attempted:           {report.executions_attempted}")
    print(f"Executions Succeeded:           {report.executions_succeeded}")
    print(f"Executions Deferred (Cooldown): {report.executions_deferred}")
    print(f"Executions Failed:              {report.executions_failed}")
    print(f"Execution Time:                 {exec_time:.3f}s")
    print("--------------------------------------------------------")
    print("FINANCIAL OUTCOMES (Paise):")
    print(f"  Total Amount at Risk:         {report.amount_at_risk_minor:,} paise")
    print(f"  Phase 6 Authorized Amount:    {report.authorized_amount_minor:,} paise")
    print(f"  Executions Attempted Amount:  {report.attempted_amount_minor:,} paise")
    print(f"  Provider Confirmed Amount:    {report.provider_confirmed_amount_minor:,} paise")
    print(f"  Confirmed Recovered Amount:   {report.recovered_amount_minor:,} paise")
    print(f"  Execution Failed Amount:      {report.failed_amount_minor:,} paise")
    print("--------------------------------------------------------")
    print("CRITICAL SAFETY RELEASE METRICS:")
    print(f"  Unauthorized Execution Rate:  {report.unauthorized_execution_rate_bps} bps (MUST BE 0)")
    print(f"  Duplicate Execution Rate:     {report.duplicate_execution_rate_bps} bps (MUST BE 0)")
    print(f"  Financial Violation Rate:     {report.financial_integrity_violation_rate_bps} bps (MUST BE 0)")
    print("========================================================")

    output_path = args.output or "docs/benchmark_execution_v1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)
    print(f"\nBenchmark results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Phase 7 Execution Benchmark CLI")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--payments", type=int, default=5000, help="Number of payments")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    asyncio.run(run_execution_benchmark(args))


if __name__ == "__main__":
    main()
