"""CLI entry point for synthetic transaction generation and database seeding."""

import argparse
import asyncio
import hashlib
import json
import time

from apps.api.core.database import AsyncSessionLocal
from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import GeneratorConfig
from data.synthetic.seeder import seed_dataset_to_database
from data.synthetic.statistics import calculate_statistics
from data.synthetic.validator import DatasetValidator


def serialize_dataset_for_hashing(dataset) -> str:
    """Canonical deterministic string representation of the dataset for SHA-256 hash generation."""
    obs = dataset.observable
    items = []
    for c in obs.customers:
        items.append(f"C:{c.id}:{c.external_customer_id}:{c.email}")
    for s in obs.subscriptions:
        items.append(f"S:{s.id}:{s.external_subscription_id}:{s.amount_minor}:{s.status.value}")
    for p in obs.payments:
        items.append(f"P:{p.id}:{p.external_payment_id}:{p.amount_minor}:{p.status.value}")
    for a in obs.payment_attempts:
        items.append(f"A:{a.id}:{a.payment_id}:{a.attempt_number}:{a.status.value}:{a.failure_code}")
    for r in obs.recovery_cases:
        items.append(f"R:{r.id}:{r.payment_id}:{r.subscription_id}:{r.amount_at_risk_minor}")
    return "\n".join(items)


def compute_dataset_hash(dataset) -> str:
    """Compute SHA-256 hash of a deterministic synthetic dataset."""
    canonical_repr = serialize_dataset_for_hashing(dataset)
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


async def main_async(args):
    config = GeneratorConfig(
        seed=args.seed,
        num_customers=args.customers,
        num_payments=args.payments,
        subscription_ratio_bps=args.sub_bps,
    )

    print(f"Generating synthetic dataset (Seed: {config.seed}, Customers: {config.num_customers}, Payments: {config.num_payments})...")
    start_time = time.time()
    generator = SyntheticDataGenerator(config)
    dataset = generator.generate()
    gen_duration = time.time() - start_time

    # Validation
    val_start = time.time()
    val_result = DatasetValidator.validate(dataset)
    val_duration = time.time() - val_start

    # Statistics
    stats = calculate_statistics(dataset)
    dataset_hash = compute_dataset_hash(dataset)

    print("\n--- Generation Report ---")
    print(f"Generation Time: {gen_duration:.3f}s")
    print(f"Validation Time: {val_duration:.3f}s (Valid: {val_result.is_valid})")
    print(f"Dataset SHA-256 Hash: {dataset_hash}")
    print("\n--- Statistics (Integer Minor Units / Paise) ---")
    print(json.dumps(stats.model_dump(), indent=2))

    if not val_result.is_valid:
        print("\nValidation Errors:")
        for err in val_result.errors:
            print(f" - {err}")
        return

    if args.seed_db:
        print("\nSeeding dataset into PostgreSQL...")
        async with AsyncSessionLocal() as session:
            count = await seed_dataset_to_database(dataset, session)
            print(f"Successfully seeded {count} records into PostgreSQL.")


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Synthetic Transaction Engine CLI")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--payments", type=int, default=5000, help="Number of payments")
    parser.add_argument("--sub-bps", type=int, default=2500, help="Subscription ratio in bps (default 2500 = 25%%)")
    parser.add_argument("--seed-db", action="store_true", help="Seed generated data into PostgreSQL")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
