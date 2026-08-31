"""PostgreSQL database tests for RecoverAI Phase 1 data model.

Tests exercise actual PostgreSQL behavior and constraints:
- CHECK constraints (monetary amounts, attempt numbers, recovery case targets)
- Foreign keys and relationships
- Unique constraints
- Status enum values
- Database session transactions and rollback
"""

import os
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from data.models import (
    Base,
    Customer,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
    Subscription,
    SubscriptionStatus,
)

from sqlalchemy.pool import NullPool

# Test PostgreSQL database URL (defaults to isolated test instance)
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@127.0.0.1:5433/recoverai_test",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create fresh isolated async engine and session per test."""
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


@pytest.mark.asyncio
async def test_1_customer_creation(db_session: AsyncSession):
    """Test 1: Verify Customer entity creation and persistence."""
    customer = Customer(
        external_customer_id="cust_test_001",
        email="merchant_user@example.com",
        name="Merchant User",
    )
    db_session.add(customer)
    await db_session.commit()

    assert customer.id is not None
    assert isinstance(customer.id, uuid.UUID)
    assert customer.created_at is not None
    assert customer.updated_at is not None


@pytest.mark.asyncio
async def test_2_payment_creation(db_session: AsyncSession):
    """Test 2: Verify Payment creation with integer minor currency units."""
    customer = Customer(
        external_customer_id="cust_test_002",
        email="payment_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_001",
        customer_id=customer.id,
        amount_minor=49900,  # ₹499.00 in paise
        currency="INR",
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.commit()

    assert payment.id is not None
    assert payment.amount_minor == 49900
    assert payment.currency == "INR"
    assert payment.status == PaymentStatus.CREATED


@pytest.mark.asyncio
async def test_3_payment_to_customer_relationship(db_session: AsyncSession):
    """Test 3: Verify Payment-to-Customer foreign key and relationship."""
    customer = Customer(
        external_customer_id="cust_test_003",
        email="rel_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_002",
        customer_id=customer.id,
        amount_minor=125050,  # ₹1,250.50
        currency="INR",
        status=PaymentStatus.AUTHORIZED,
    )
    db_session.add(payment)
    await db_session.commit()

    # Re-fetch customer
    fetched_customer = await db_session.get(Customer, customer.id)
    assert fetched_customer is not None
    assert payment.customer.id == customer.id


@pytest.mark.asyncio
async def test_4_multiple_payment_attempts_for_one_payment(db_session: AsyncSession):
    """Test 4: Verify multiple PaymentAttempts can belong to one Payment."""
    customer = Customer(
        external_customer_id="cust_test_004",
        email="attempts_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_003",
        customer_id=customer.id,
        amount_minor=50000,
        currency="INR",
        status=PaymentStatus.FAILED,
    )
    db_session.add(payment)
    await db_session.flush()

    attempt1 = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        status=PaymentAttemptStatus.FAILED,
        failure_code="CARD_DECLINED",
        failure_reason="Insufficient funds",
    )
    attempt2 = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=2,
        status=PaymentAttemptStatus.INITIATED,
    )
    db_session.add_all([attempt1, attempt2])
    await db_session.commit()

    assert attempt1.attempt_number == 1
    assert attempt2.attempt_number == 2
    assert attempt1.payment_id == payment.id
    assert attempt2.payment_id == payment.id


@pytest.mark.asyncio
async def test_5_successful_payment_attempt(db_session: AsyncSession):
    """Test 5: Verify successful PaymentAttempt with null failure fields."""
    customer = Customer(
        external_customer_id="cust_test_005",
        email="success_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_004",
        customer_id=customer.id,
        amount_minor=200000,
        currency="INR",
        status=PaymentStatus.CAPTURED,
    )
    db_session.add(payment)
    await db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        status=PaymentAttemptStatus.SUCCESSFUL,
        failure_code=None,
        failure_reason=None,
    )
    db_session.add(attempt)
    await db_session.commit()

    assert attempt.status == PaymentAttemptStatus.SUCCESSFUL
    assert attempt.failure_code is None
    assert attempt.failure_reason is None


@pytest.mark.asyncio
async def test_6_failed_payment_attempt(db_session: AsyncSession):
    """Test 6: Verify failed PaymentAttempt with failure code and reason."""
    customer = Customer(
        external_customer_id="cust_test_006",
        email="fail_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_005",
        customer_id=customer.id,
        amount_minor=10000,
        currency="INR",
        status=PaymentStatus.FAILED,
    )
    db_session.add(payment)
    await db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        status=PaymentAttemptStatus.FAILED,
        failure_code="EXPIRED_CARD",
        failure_reason="Card expired on 2026-05",
    )
    db_session.add(attempt)
    await db_session.commit()

    assert attempt.status == PaymentAttemptStatus.FAILED
    assert attempt.failure_code == "EXPIRED_CARD"
    assert attempt.failure_reason == "Card expired on 2026-05"


@pytest.mark.asyncio
async def test_7_subscription_to_customer_relationship(db_session: AsyncSession):
    """Test 7: Verify Subscription-to-Customer relationship and fields."""
    customer = Customer(
        external_customer_id="cust_test_007",
        email="sub_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    subscription = Subscription(
        external_subscription_id="sub_test_001",
        customer_id=customer.id,
        amount_minor=99900,  # ₹999.00
        currency="INR",
        status=SubscriptionStatus.ACTIVE,
        interval="monthly",
    )
    db_session.add(subscription)
    await db_session.commit()

    assert subscription.id is not None
    assert subscription.customer.id == customer.id
    assert subscription.amount_minor == 99900
    assert subscription.interval == "monthly"


@pytest.mark.asyncio
async def test_8_recovery_case_referencing_payment(db_session: AsyncSession):
    """Test 8: Verify RecoveryCase referencing a Payment (and no Subscription)."""
    customer = Customer(
        external_customer_id="cust_test_008",
        email="rc_pay_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_006",
        customer_id=customer.id,
        amount_minor=75000,
        currency="INR",
        status=PaymentStatus.FAILED,
    )
    db_session.add(payment)
    await db_session.flush()

    rc = RecoveryCase(
        payment_id=payment.id,
        subscription_id=None,
        status=RecoveryCaseStatus.DETECTED,
        amount_at_risk_minor=75000,
        currency="INR",
    )
    db_session.add(rc)
    await db_session.commit()

    assert rc.id is not None
    assert rc.payment_id == payment.id
    assert rc.subscription_id is None
    assert rc.amount_at_risk_minor == 75000


@pytest.mark.asyncio
async def test_9_recovery_case_referencing_subscription(db_session: AsyncSession):
    """Test 9: Verify RecoveryCase referencing a Subscription (and no Payment)."""
    customer = Customer(
        external_customer_id="cust_test_009",
        email="rc_sub_user@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    subscription = Subscription(
        external_subscription_id="sub_test_002",
        customer_id=customer.id,
        amount_minor=199900,
        currency="INR",
        status=SubscriptionStatus.PAST_DUE,
        interval="yearly",
    )
    db_session.add(subscription)
    await db_session.flush()

    rc = RecoveryCase(
        payment_id=None,
        subscription_id=subscription.id,
        status=RecoveryCaseStatus.DETECTED,
        amount_at_risk_minor=199900,
        currency="INR",
    )
    db_session.add(rc)
    await db_session.commit()

    assert rc.id is not None
    assert rc.payment_id is None
    assert rc.subscription_id == subscription.id


@pytest.mark.asyncio
async def test_10_recovery_case_neither_target_rejected(db_session: AsyncSession):
    """Test 10: Verify RecoveryCase referencing neither Payment nor Subscription is rejected by DB constraint."""
    rc = RecoveryCase(
        payment_id=None,
        subscription_id=None,
        status=RecoveryCaseStatus.DETECTED,
        amount_at_risk_minor=50000,
        currency="INR",
    )
    db_session.add(rc)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_11_recovery_case_both_targets_rejected(db_session: AsyncSession):
    """Test 11: Verify RecoveryCase referencing BOTH Payment and Subscription is rejected by exactly-one target constraint."""
    customer = Customer(
        external_customer_id="cust_test_011",
        email="both_targets@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_test_011",
        customer_id=customer.id,
        amount_minor=50000,
        currency="INR",
        status=PaymentStatus.FAILED,
    )
    subscription = Subscription(
        external_subscription_id="sub_test_011",
        customer_id=customer.id,
        amount_minor=50000,
        currency="INR",
        status=SubscriptionStatus.ACTIVE,
        interval="monthly",
    )
    db_session.add_all([payment, subscription])
    await db_session.flush()

    rc = RecoveryCase(
        payment_id=payment.id,
        subscription_id=subscription.id,
        status=RecoveryCaseStatus.DETECTED,
        amount_at_risk_minor=50000,
        currency="INR",
    )
    db_session.add(rc)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_12_negative_payment_amount_rejected(db_session: AsyncSession):
    """Test 12: Verify negative payment amount is rejected by PostgreSQL CHECK constraint."""
    customer = Customer(
        external_customer_id="cust_test_012",
        email="neg_pay@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_neg_001",
        customer_id=customer.id,
        amount_minor=-100,  # Negative money
        currency="INR",
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_13_negative_subscription_amount_rejected(db_session: AsyncSession):
    """Test 13: Verify negative subscription amount is rejected by PostgreSQL CHECK constraint."""
    customer = Customer(
        external_customer_id="cust_test_013",
        email="neg_sub@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    subscription = Subscription(
        external_subscription_id="sub_neg_001",
        customer_id=customer.id,
        amount_minor=-500,  # Negative money
        currency="INR",
        status=SubscriptionStatus.ACTIVE,
        interval="monthly",
    )
    db_session.add(subscription)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_14_invalid_attempt_number_rejected(db_session: AsyncSession):
    """Test 14: Verify zero/negative attempt number is rejected by PostgreSQL CHECK constraint."""
    customer = Customer(
        external_customer_id="cust_test_014",
        email="zero_attempt@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    payment = Payment(
        external_payment_id="pay_attempt_001",
        customer_id=customer.id,
        amount_minor=10000,
        currency="INR",
        status=PaymentStatus.FAILED,
    )
    db_session.add(payment)
    await db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=0,  # Invalid attempt number <= 0
        status=PaymentAttemptStatus.INITIATED,
    )
    db_session.add(attempt)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_15_duplicate_external_customer_id_rejected(db_session: AsyncSession):
    """Test 15: Verify duplicate external customer ID is rejected by UNIQUE constraint."""
    cust1 = Customer(
        external_customer_id="cust_dup_001",
        email="user1@example.com",
    )
    cust2 = Customer(
        external_customer_id="cust_dup_001",  # Duplicate
        email="user2@example.com",
    )
    db_session.add(cust1)
    await db_session.commit()

    db_session.add(cust2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_16_duplicate_external_payment_id_rejected(db_session: AsyncSession):
    """Test 16: Verify duplicate external payment ID is rejected by UNIQUE constraint."""
    customer = Customer(
        external_customer_id="cust_test_016",
        email="pay_dup@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    pay1 = Payment(
        external_payment_id="pay_dup_001",
        customer_id=customer.id,
        amount_minor=10000,
        currency="INR",
        status=PaymentStatus.CREATED,
    )
    pay2 = Payment(
        external_payment_id="pay_dup_001",  # Duplicate
        customer_id=customer.id,
        amount_minor=20000,
        currency="INR",
        status=PaymentStatus.CREATED,
    )
    db_session.add(pay1)
    await db_session.commit()

    db_session.add(pay2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_17_duplicate_external_subscription_id_rejected(db_session: AsyncSession):
    """Test 17: Verify duplicate external subscription ID is rejected by UNIQUE constraint."""
    customer = Customer(
        external_customer_id="cust_test_017",
        email="sub_dup@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    sub1 = Subscription(
        external_subscription_id="sub_dup_001",
        customer_id=customer.id,
        amount_minor=50000,
        currency="INR",
        status=SubscriptionStatus.ACTIVE,
        interval="monthly",
    )
    sub2 = Subscription(
        external_subscription_id="sub_dup_001",  # Duplicate
        customer_id=customer.id,
        amount_minor=60000,
        currency="INR",
        status=SubscriptionStatus.ACTIVE,
        interval="monthly",
    )
    db_session.add(sub1)
    await db_session.commit()

    db_session.add(sub2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_18_invalid_status_value_rejected(db_session: AsyncSession):
    """Test 18: Verify invalid status values cannot silently enter the database."""
    customer = Customer(
        external_customer_id="cust_test_018",
        email="invalid_status@example.com",
    )
    db_session.add(customer)
    await db_session.flush()

    # Attempt direct raw SQL insert of invalid status
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.execute(
            text(
                "INSERT INTO payments (id, external_payment_id, customer_id, amount_minor, currency, status) "
                "VALUES (:id, :ext_id, :cust_id, :amt, :curr, :status)"
            ),
            {
                "id": uuid.uuid4(),
                "ext_id": "pay_invalid_status_001",
                "cust_id": customer.id,
                "amt": 10000,
                "curr": "INR",
                "status": "NON_EXISTENT_STATUS_VALUE",
            },
        )
        await db_session.commit()
