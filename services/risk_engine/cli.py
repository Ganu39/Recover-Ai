"""Benchmark CLI tool for evaluating Deterministic Revenue-Risk Engine against synthetic data."""

import argparse
import json
import time

from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from services.risk_engine.evaluator import BaselineEvaluator
from services.risk_engine.models import BASELINE_VERSION


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Baseline Risk Engine Benchmark CLI")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--payments", type=int, default=5000, help="Number of payments")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path for benchmark report")
    args = parser.parse_args()

    config = GeneratorConfig(seed=args.seed, num_customers=args.customers, num_payments=args.payments)
    print(f"Generating synthetic dataset (Seed: {config.seed}, Customers: {config.num_customers}, Payments: {config.num_payments})...")
    gen_start = time.time()
    dataset = SyntheticDataGenerator(config).generate()
    gen_time = time.time() - gen_start

    print(f"Evaluating Baseline ({BASELINE_VERSION}) over {len(dataset.observable.recovery_cases)} recovery cases...")
    eval_start = time.time()
    evaluator = BaselineEvaluator()
    metrics = evaluator.evaluate_dataset(dataset)
    eval_time = time.time() - eval_start

    print("\n========================================================")
    print(f"  RECOVERAI — BASELINE BENCHMARK REPORT ({BASELINE_VERSION})")
    print("========================================================")
    print(f"Dataset Seed:           {metrics.dataset_seed}")
    print(f"Evaluated Cases:        {metrics.evaluated_cases_count}")
    print(f"Generation Time:        {gen_time:.3f}s")
    print(f"Evaluation Time:        {eval_time:.3f}s")
    print("--------------------------------------------------------")
    print("CONFUSION MATRIX:")
    print(f"  True Positives (TP):  {metrics.true_positives}")
    print(f"  False Positives (FP): {metrics.false_positives}")
    print(f"  True Negatives (TN):  {metrics.true_negatives}")
    print(f"  False Negatives (FN): {metrics.false_negatives}")
    print("--------------------------------------------------------")
    print("STATISTICAL PERFORMANCE (Basis Points):")
    print(f"  Precision:            {metrics.precision_bps} bps ({metrics.precision_bps / 100:.2f}%)")
    print(f"  Recall:               {metrics.recall_bps} bps ({metrics.recall_bps / 100:.2f}%)")
    print(f"  F1 Score:             {metrics.f1_score_bps} bps ({metrics.f1_score_bps / 100:.2f}%)")
    print(f"  Accuracy:             {metrics.accuracy_bps} bps ({metrics.accuracy_bps / 100:.2f}%)")
    print("--------------------------------------------------------")
    print("FINANCIAL METRICS (Integer Paise):")
    print(f"  Total Amount at Risk:        {metrics.total_amount_at_risk_minor:,} paise")
    print(f"  Recoverable Amount Captured: {metrics.recoverable_amount_captured_minor:,} paise")
    print(f"  Recoverable Amount Missed:   {metrics.recoverable_amount_missed_minor:,} paise")
    print(f"  False Intervention Amount:   {metrics.false_intervention_amount_minor:,} paise")
    print(f"  Revenue Capture Rate:        {metrics.revenue_capture_rate_bps} bps ({metrics.revenue_capture_rate_bps / 100:.2f}%)")
    print("========================================================")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(metrics.model_dump(), f, indent=2)
        print(f"\nBenchmark results saved to: {args.output}")


if __name__ == "__main__":
    main()
