"""Payment and PaymentAttempt entity models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.models.base import Base
from data.models.enums import PaymentAttemptStatus, PaymentStatus

if TYPE_CHECKING:
    from data.models.customer import Customer
    from data.models.recovery_case import RecoveryCase


class Payment(Base):
    """Represents the logical payment/order amount a customer is attempting to pay."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "amount_minor >= 0",
            name="ck_payment_amount_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_payment_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    amount_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, length=50, create_constraint=True),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="payments",
    )
    attempts: Mapped[List["PaymentAttempt"]] = relationship(
        "PaymentAttempt",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentAttempt.attempt_number",
    )
    recovery_cases: Mapped[List["RecoveryCase"]] = relationship(
        "RecoveryCase",
        back_populates="payment",
    )


class PaymentAttempt(Base):
    """Represents an individual payment attempt associated with a Payment."""

    __tablename__ = "payment_attempts"
    __table_args__ = (
        CheckConstraint(
            "attempt_number > 0",
            name="ck_payment_attempt_number_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[PaymentAttemptStatus] = mapped_column(
        SAEnum(PaymentAttemptStatus, native_enum=False, length=50, create_constraint=True),
        nullable=False,
    )
    failure_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="attempts",
    )
