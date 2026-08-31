"""CLI benchmark tool for Phase 5 Recovery Decision Agent."""

import argparse
import asyncio
import json
import time

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from agents.decision.evaluator import RecoveryDecisionEvaluator
from agents.decision.policy import DEFAULT_RECOVERY_POLICY


async def main_async(args):
    config = GeneratorConfig(seed=args.seed, num_customers=args.customers, num_payments=args.payments)
    print(f"Generating synthetic dataset (Seed: {config.seed}, Customers: {config.num_customers}, Payments: {config.num_payments})...")
    gen_start = time.time()
    dataset = SyntheticDataGenerator(config).generate()
    gen_time = time.time() - gen_start

    print(f"Evaluating Recovery Decision Agent ({DEFAULT_RECOVERY_POLICY.policy_version}) on {len(dataset.observable.recovery_cases)} cases...")
    eval_start = time.time()
    evaluator = RecoveryDecisionEvaluator()
    report = await evaluator.evaluate_dataset(dataset, policy=DEFAULT_RECOVERY_POLICY)
    eval_time = time.time() - eval_start

    print("\n========================================================")
    print(f"  RECOVERAI — RECOVERY DECISION BENCHMARK ({report.decision_version}/{report.policy_version})")
    print("========================================================")
    print(f"Dataset Seed:               {report.dataset_seed}")
    print(f"Evaluated Proposals:        {report.evaluated_proposals_count}")
    print(f"Execution Time:             {eval_time:.3f}s")
    print("--------------------------------------------------------")
    print("ACTION TYPE DISTRIBUTION:")
    for action, count in sorted(report.action_type_counts.items()):
        print(f"  {action:<30}: {count:>5}")
    print("--------------------------------------------------------")
    print("DECISION STATUS DISTRIBUTION:")
    for status, count in sorted(report.decision_status_counts.items()):
        print(f"  {status:<30}: {count:>5}")
    print("--------------------------------------------------------")
    print("FINANCIAL EXPOSURE BY STATUS (Integer Minor / Paise):")
    print(f"  Total Amount at Risk:     {report.total_amount_at_risk_minor:,} paise")
    print(f"  Proposed Action Amount:   {report.proposed_action_amount_minor:,} paise")
    print(f"  Human Review Amount:      {report.human_review_amount_minor:,} paise")
    print(f"  Blocked Action Amount:    {report.blocked_action_amount_minor:,} paise")
    print(f"  No Action Amount:         {report.no_action_amount_minor:,} paise")
    print("--------------------------------------------------------")
    print("SAFETY & POLICY INVARIANTS:")
    print(f"  Human Review Rate:        {report.human_review_escalation_rate_bps} bps ({report.human_review_escalation_rate_bps / 100:.2f}%)")
    print(f"  Blocked Rate:             {report.blocked_rate_bps} bps ({report.blocked_rate_bps / 100:.2f}%)")
    print(f"  Unsafe Proposals (MUST=0):{report.unsafe_action_proposal_count}")
    print("========================================================")

    output_path = args.output or "docs/benchmark_decision_v1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)
    print(f"\nBenchmark results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Recovery Decision Benchmark CLI")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--payments", type=int, default=5000, help="Number of payments")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
