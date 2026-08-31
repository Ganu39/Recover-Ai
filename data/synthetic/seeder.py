"""Database seeder for inserting synthetic datasets into PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncSession
from data.synthetic.models import SyntheticDataset


async def seed_dataset_to_database(dataset: SyntheticDataset, session: AsyncSession) -> int:
    """Seed observable entities from a synthetic dataset into PostgreSQL within a single transaction.

    Note: Ground-truth evaluation metadata is strictly excluded from database insertion.
    """
    obs = dataset.observable
    total_records = (
        len(obs.customers)
        + len(obs.subscriptions)
        + len(obs.payments)
        + len(obs.payment_attempts)
        + len(obs.recovery_cases)
    )

    # 1. Add Customers
    for customer in obs.customers:
        session.add(customer)
    await session.flush()

    # 2. Add Subscriptions
    for subscription in obs.subscriptions:
        session.add(subscription)
    await session.flush()

    # 3. Add Payments
    for payment in obs.payments:
        session.add(payment)
    await session.flush()

    # 4. Add PaymentAttempts
    for attempt in obs.payment_attempts:
        session.add(attempt)
    await session.flush()

    # 5. Add RecoveryCases (Production fields only)
    for rc in obs.recovery_cases:
        session.add(rc)
    await session.flush()

    await session.commit()
    return total_records
