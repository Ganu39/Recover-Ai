"""CLI benchmark runner for Phase 4 AI Root-Cause Diagnosis."""

import argparse
import asyncio
import json
import time

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from agents.diagnosis.evaluator import AIDiagnosisEvaluator
from agents.diagnosis.providers.mock import MockLLMProvider
from agents.diagnosis.service import DiagnosisAgent


async def main_async(args):
    config = GeneratorConfig(seed=args.seed, num_customers=args.customers, num_payments=args.payments)
    print(f"Generating synthetic dataset (Seed: {config.seed}, Customers: {config.num_customers}, Payments: {config.num_payments})...")
    gen_start = time.time()
    dataset = SyntheticDataGenerator(config).generate()
    gen_time = time.time() - gen_start

    # Provider initialization
    is_mock = True
    provider = MockLLMProvider()
    agent = DiagnosisAgent(provider=provider, prompt_version="v1")

    print(f"Running Diagnosis Agent ({provider.provider_name}/{provider.model_name}) on {len(dataset.observable.recovery_cases)} cases...")
    eval_start = time.time()
    evaluator = AIDiagnosisEvaluator()
    report = await evaluator.evaluate_dataset(dataset, agent, is_mock=is_mock)
    eval_time = time.time() - eval_start

    print("\n========================================================")
    print(f"  RECOVERAI — AI DIAGNOSIS EVALUATION ({report.benchmark_type})")
    print("========================================================")
    print(f"Provider / Model:       {report.provider_name} / {report.model_name}")
    print(f"Prompt Version:         {report.prompt_version}")
    print(f"Dataset Seed:           {report.dataset_seed}")
    print(f"Evaluated Cases:        {report.evaluated_cases_count}")
    print(f"Execution Time:         {eval_time:.3f}s")
    print("--------------------------------------------------------")
    print("EXECUTION INTEGRITY:")
    print(f"  Successful:           {report.successful_executions}")
    print(f"  Failed / Fallback:    {report.failed_executions}")
    print(f"  Schema Validity:      {report.schema_validity_rate_bps} bps ({report.schema_validity_rate_bps / 100:.2f}%)")
    print(f"  Evidence Grounding:   {report.evidence_grounding_rate_bps} bps ({report.evidence_grounding_rate_bps / 100:.2f}%)")
    print("--------------------------------------------------------")
    print("RECOVERABILITY CLASSIFICATION (Basis Points):")
    print(f"  Precision:            {report.precision_bps} bps ({report.precision_bps / 100:.2f}%)")
    print(f"  Recall:               {report.recall_bps} bps ({report.recall_bps / 100:.2f}%)")
    print(f"  F1 Score:             {report.f1_score_bps} bps ({report.f1_score_bps / 100:.2f}%)")
    print("--------------------------------------------------------")
    print("COMPARISON WITH DETERMINISTIC BASELINE v1:")
    print(f"  Baseline v1 F1:       {report.baseline_v1_f1_score_bps} bps ({report.baseline_v1_f1_score_bps / 100:.2f}%)")
    print(f"  F1 Delta:             {report.f1_score_delta_bps:+d} bps ({report.f1_score_delta_bps / 100:+.2f}%)")
    print(f"  Baseline v1 Capture:  {report.baseline_v1_revenue_capture_rate_bps} bps")
    print(f"  Revenue Capture Delta:{report.revenue_capture_delta_bps:+d} bps ({report.revenue_capture_delta_bps / 100:+.2f}%)")
    print("========================================================")

    output_path = args.output or ("docs/benchmark_ai_mock.json" if is_mock else "docs/benchmark_ai_v1.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)
    print(f"\nReport written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="RecoverAI AI Diagnosis Benchmark CLI")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--payments", type=int, default=5000, help="Number of payments")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
