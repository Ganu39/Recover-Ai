"""CLI benchmark tool for Phase 6 Deterministic Policy & Safety Gateway."""

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
from agents.gateway.schemas import GatewayTargetContext, HumanApprovalRecord
from services.risk_engine.extractor import ObservableFeatureExtractor


async def run_gateway_benchmark(args):
    config = GeneratorConfig(seed=args.seed, num_customers=args.customers, num_payments=args.payments)
    print(f"Generating synthetic dataset (Seed: {config.seed}, Customers: {config.num_customers}, Payments: {config.num_payments})...")
    gen_start = time.time()
    dataset = SyntheticDataGenerator(config).generate()
    gen_time = time.time() - gen_start

    print(f"Extracting contexts & generating Phase 4 AI diagnoses for {len(dataset.observable.recovery_cases)} cases...")
    obs_contexts = ObservableFeatureExtractor.extract_from_dataset(dataset.observable)
    ai_contexts = AIDiagnosisContextBuilder.build_from_dataset(dataset.observable)

    diagnosis_agent = DiagnosisAgent(provider=MockLLMProvider(), prompt_version="v1")
    ai_diagnoses = await diagnosis_agent.diagnose_batch(ai_contexts)
    ai_diag_map = {d.case_id: d for d in ai_diagnoses if d.case_id}

    print("Synthesizing Phase 5 Decision Proposals...")
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

    print(f"Evaluating Deterministic Policy & Safety Gateway on {len(proposals)} proposals...")
    eval_start = time.time()
    evaluator = GatewayEvaluator()
    triplets: List[Tuple[RecoveryDecisionProposal, GatewayTargetContext, Optional[HumanApprovalRecord]]] = [
        (prop, tgt, None) for prop, tgt in zip(proposals, target_contexts)
    ]
    results, report = evaluator.evaluate(triplets)
    eval_time = time.time() - eval_start

    print("\n========================================================")
    print(f"  RECOVERAI — SAFETY GATEWAY BENCHMARK ({report.gateway_version}/{report.policy_version})")
    print("========================================================")
    print(f"Dataset Seed:                  {args.seed}")
    print(f"Evaluated Proposals:           {report.total_evaluated}")
    print(f"Execution Time:                {eval_time:.3f}s")
    print("--------------------------------------------------------")
    print("GATEWAY DECISION BREAKDOWN:")
    print(f"  APPROVED:                    {report.approved_count:>5} ({report.decision_distribution_bps.get('APPROVED', 0)} bps)")
    print(f"  BLOCKED:                     {report.blocked_count:>5} ({report.decision_distribution_bps.get('BLOCKED', 0)} bps)")
    print(f"  REQUIRES_REVIEW:             {report.requires_review_count:>5} ({report.decision_distribution_bps.get('REQUIRES_REVIEW', 0)} bps)")
    print(f"  RATE_LIMITED:                {report.rate_limited_count:>5} ({report.decision_distribution_bps.get('RATE_LIMITED', 0)} bps)")
    print(f"  KILL_SWITCH_ACTIVE:          {report.kill_switch_count:>5} ({report.decision_distribution_bps.get('KILL_SWITCH_ACTIVE', 0)} bps)")
    print(f"  INVALID_PROPOSAL:            {report.invalid_proposal_count:>5} ({report.decision_distribution_bps.get('INVALID_PROPOSAL', 0)} bps)")
    print("--------------------------------------------------------")
    print("FINANCIAL EXPOSURE (Paise):")
    for k, v in report.financial_metrics_paise.items():
        print(f"  {k:<28}: {v:,} paise")
    print("--------------------------------------------------------")
    print("CRITICAL SAFETY INVARIANTS:")
    print(f"  Unsafe Authorizations:       {report.unsafe_authorizations} (MUST BE 0)")
    print(f"  Unsafe Authorization Rate:   {report.unsafe_authorization_rate_bps} bps (MUST BE 0 bps)")
    print(f"  Financial Violations:        {report.financial_integrity_violations} (MUST BE 0)")
    print("========================================================")

    output_path = args.output or "docs/benchmark_gateway_v1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)
    print(f"\nBenchmark results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Phase 6 Safety Gateway Benchmark CLI")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--payments", type=int, default=5000, help="Number of payments")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    asyncio.run(run_gateway_benchmark(args))


if __name__ == "__main__":
    main()
