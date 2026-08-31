"""Automated tests for RecoverAI Phase 2 Synthetic Transaction Engine."""

import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from data.models import Base
from data.synthetic import (
    DatasetValidator,
    GeneratorConfig,
    ScenarioType,
    SyntheticDataGenerator,
    calculate_statistics,
    compute_dataset_hash,
    seed_dataset_to_database,
)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@127.0.0.1:5433/recoverai_test",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create isolated async session for database seeding test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def test_1_same_seed_produces_identical_dataset():
    """Test 1: Verify bit-for-bit identical dataset and hash given same seed."""
    config1 = GeneratorConfig(seed=42, num_customers=30, num_payments=100)
    config2 = GeneratorConfig(seed=42, num_customers=30, num_payments=100)

    dataset1 = SyntheticDataGenerator(config1).generate()
    dataset2 = SyntheticDataGenerator(config2).generate()

    hash1 = compute_dataset_hash(dataset1)
    hash2 = compute_dataset_hash(dataset2)

    assert hash1 == hash2
    assert len(dataset1.observable.customers) == len(dataset2.observable.customers)
    assert len(dataset1.observable.payments) == len(dataset2.observable.payments)
    assert len(dataset1.ground_truth) == len(dataset2.ground_truth)


def test_2_different_seed_produces_different_dataset():
    """Test 2: Verify different seed produces distinct dataset and hash."""
    config1 = GeneratorConfig(seed=42, num_customers=30, num_payments=100)
    config2 = GeneratorConfig(seed=999, num_customers=30, num_payments=100)

    dataset1 = SyntheticDataGenerator(config1).generate()
    dataset2 = SyntheticDataGenerator(config2).generate()

    hash1 = compute_dataset_hash(dataset1)
    hash2 = compute_dataset_hash(dataset2)

    assert hash1 != hash2


def test_3_exact_configurable_customer_count():
    """Test 3: Verify exact customer count is generated."""
    for count in [10, 55, 120]:
        config = GeneratorConfig(seed=42, num_customers=count, num_payments=count * 2)
        dataset = SyntheticDataGenerator(config).generate()
        assert len(dataset.observable.customers) == count


def test_4_exact_configurable_payment_count():
    """Test 4: Verify exact payment count is generated."""
    for count in [25, 100, 250]:
        config = GeneratorConfig(seed=42, num_customers=20, num_payments=count)
        dataset = SyntheticDataGenerator(config).generate()
        assert len(dataset.observable.payments) == count


def test_5_customer_relationships_valid():
    """Test 5: Verify all foreign keys and customer linkages."""
    config = GeneratorConfig(seed=42, num_customers=30, num_payments=120)
    dataset = SyntheticDataGenerator(config).generate()
    cust_ids = {c.id for c in dataset.observable.customers}

    for p in dataset.observable.payments:
        assert p.customer_id in cust_ids

    for s in dataset.observable.subscriptions:
        assert s.customer_id in cust_ids


def test_6_payment_attempts_valid():
    """Test 6: Verify payment attempts belong to valid payments."""
    config = GeneratorConfig(seed=42, num_customers=30, num_payments=120)
    dataset = SyntheticDataGenerator(config).generate()
    pay_ids = {p.id for p in dataset.observable.payments}

    assert len(dataset.observable.payment_attempts) >= len(dataset.observable.payments)
    for att in dataset.observable.payment_attempts:
        assert att.payment_id in pay_ids


def test_7_attempt_numbers_positive_and_ordered():
    """Test 7: Verify attempt numbers are positive integers in sequential order."""
    config = GeneratorConfig(seed=42, num_customers=30, num_payments=120)
    dataset = SyntheticDataGenerator(config).generate()

    attempts_by_pay = {}
    for att in dataset.observable.payment_attempts:
        assert att.attempt_number > 0
        attempts_by_pay.setdefault(att.payment_id, []).append(att.attempt_number)

    for pay_id, nums in attempts_by_pay.items():
        assert sorted(nums) == list(range(1, len(nums) + 1))


def test_8_recovery_scenarios_have_exactly_one_target():
    """Test 8: Verify every RecoveryCase has exactly one target (payment XOR subscription)."""
    config = GeneratorConfig(seed=42, num_customers=50, num_payments=200)
    dataset = SyntheticDataGenerator(config).generate()

    assert len(dataset.observable.recovery_cases) > 0
    for rc in dataset.observable.recovery_cases:
        has_pay = rc.payment_id is not None
        has_sub = rc.subscription_id is not None
        assert has_pay ^ has_sub, f"RecoveryCase {rc.id} target violation"


def test_9_amounts_are_non_negative_integer_minor():
    """Test 9: Verify all monetary values are non-negative integers."""
    config = GeneratorConfig(seed=42, num_customers=30, num_payments=100)
    dataset = SyntheticDataGenerator(config).generate()

    for p in dataset.observable.payments:
        assert isinstance(p.amount_minor, int)
        assert p.amount_minor >= 0

    for s in dataset.observable.subscriptions:
        assert isinstance(s.amount_minor, int)
        assert s.amount_minor >= 0

    for rc in dataset.observable.recovery_cases:
        assert isinstance(rc.amount_at_risk_minor, int)
        assert rc.amount_at_risk_minor >= 0


def test_10_timestamps_are_logically_ordered():
    """Test 10: Verify chronological order across entity hierarchy."""
    config = GeneratorConfig(seed=42, num_customers=30, num_payments=100)
    dataset = SyntheticDataGenerator(config).generate()

    cust_map = {c.id: c.created_at for c in dataset.observable.customers}
    pay_map = {p.id: p.created_at for p in dataset.observable.payments}

    for p in dataset.observable.payments:
        assert p.created_at >= cust_map[p.customer_id]

    for att in dataset.observable.payment_attempts:
        assert att.attempted_at >= pay_map[att.payment_id]


def test_11_external_ids_are_unique():
    """Test 11: Verify external customer, payment, and subscription IDs are unique."""
    config = GeneratorConfig(seed=42, num_customers=50, num_payments=200)
    dataset = SyntheticDataGenerator(config).generate()

    cust_ext_ids = [c.external_customer_id for c in dataset.observable.customers]
    pay_ext_ids = [p.external_payment_id for p in dataset.observable.payments]
    sub_ext_ids = [s.external_subscription_id for s in dataset.observable.subscriptions]

    assert len(cust_ext_ids) == len(set(cust_ext_ids))
    assert len(pay_ext_ids) == len(set(pay_ext_ids))
    assert len(sub_ext_ids) == len(set(sub_ext_ids))


def test_12_ground_truth_is_deterministic():
    """Test 12: Verify ground truth evaluation records are deterministic across runs."""
    config1 = GeneratorConfig(seed=42, num_customers=30, num_payments=100)
    config2 = GeneratorConfig(seed=42, num_customers=30, num_payments=100)

    ds1 = SyntheticDataGenerator(config1).generate()
    ds2 = SyntheticDataGenerator(config2).generate()

    gt1 = [(gt.case_id, gt.scenario_type, gt.is_recoverable) for gt in ds1.ground_truth]
    gt2 = [(gt.case_id, gt.scenario_type, gt.is_recoverable) for gt in ds2.ground_truth]

    assert gt1 == gt2


def test_13_ground_truth_not_exposed_in_observable_payload():
    """Test 13: Verify ground truth field names and values are completely absent from observable payloads."""
    config = GeneratorConfig(seed=42, num_customers=20, num_payments=50)
    dataset = SyntheticDataGenerator(config).generate()

    # Inspect observable dataset serialized dict
    obs_dict = dataset.observable.model_dump()
    forbidden_keys = {"scenario_type", "is_recoverable", "expected_recovery_reason", "ground_truth"}

    def check_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in forbidden_keys, f"Ground truth leakage: found key '{k}' in observable dataset"
                check_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                check_keys(item)

    check_keys(obs_dict)


def test_14_data_quality_validator_passes():
    """Test 14: Verify DatasetValidator passes with 0 errors on generated dataset."""
    config = GeneratorConfig(seed=42, num_customers=50, num_payments=200)
    dataset = SyntheticDataGenerator(config).generate()
    val_result = DatasetValidator.validate(dataset)

    assert val_result.is_valid is True
    assert len(val_result.errors) == 0


def test_15_dataset_statistics_reconcile():
    """Test 15: Verify summary statistics reconcile with generated records."""
    config = GeneratorConfig(seed=42, num_customers=50, num_payments=200)
    dataset = SyntheticDataGenerator(config).generate()
    stats = calculate_statistics(dataset)

    assert stats.customers_count == 50
    assert stats.payments_count == 200
    assert stats.successful_payments_count + stats.failed_payments_count == 200
    assert stats.recoverable_cases_count + stats.non_recoverable_cases_count == stats.recovery_cases_count
    assert stats.recoverable_amount_minor + stats.non_recoverable_amount_minor == stats.amount_at_risk_minor


def test_16_all_scenarios_can_be_generated():
    """Test 16: Verify all eight scenario archetypes appear in generated dataset."""
    config = GeneratorConfig(seed=42, num_customers=200, num_payments=800)
    dataset = SyntheticDataGenerator(config).generate()
    stats = calculate_statistics(dataset)

    for scenario_enum in ScenarioType:
        assert stats.scenario_counts.get(scenario_enum.value, 0) > 0, (
            f"Scenario archetype {scenario_enum.value} was not generated"
        )


def test_17_decoupled_profiles_and_scenarios():
    """Test 17: Verify multiple profiles produce both recoverable and non-recoverable outcomes."""
    config = GeneratorConfig(seed=42, num_customers=100, num_payments=400)
    dataset = SyntheticDataGenerator(config).generate()

    assert any(gt.is_recoverable for gt in dataset.ground_truth)
    assert any(not gt.is_recoverable for gt in dataset.ground_truth)


@pytest.mark.asyncio
async def test_18_postgresql_seeding_works(db_session: AsyncSession):
    """Test 18: Verify small synthetic dataset can be seeded into PostgreSQL without constraint errors."""
    config = GeneratorConfig(seed=42, num_customers=15, num_payments=50)
    dataset = SyntheticDataGenerator(config).generate()

    records_seeded = await seed_dataset_to_database(dataset, db_session)
    assert records_seeded > 0
