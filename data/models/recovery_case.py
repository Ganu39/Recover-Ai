"""RecoveryCase entity model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.models.base import Base
from data.models.enums import RecoveryCaseStatus

if TYPE_CHECKING:
    from data.models.payment import Payment
    from data.models.subscription import Subscription


class RecoveryCase(Base):
    """Represents a potential revenue recovery opportunity.

    Invariant: A RecoveryCase must reference EXACTLY ONE target (either Payment or Subscription).
    """

    __tablename__ = "recovery_cases"
    __table_args__ = (
        CheckConstraint(
            "amount_at_risk_minor >= 0",
            name="ck_recovery_case_amount_non_negative",
        ),
        CheckConstraint(
            "(payment_id IS NOT NULL AND subscription_id IS NULL) OR "
            "(payment_id IS NULL AND subscription_id IS NOT NULL)",
            name="ck_recovery_case_target_exactly_one",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    status: Mapped[RecoveryCaseStatus] = mapped_column(
        SAEnum(RecoveryCaseStatus, native_enum=False, length=50, create_constraint=True),
        index=True,
        nullable=False,
    )
    amount_at_risk_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment",
        back_populates="recovery_cases",
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="recovery_cases",
    )
