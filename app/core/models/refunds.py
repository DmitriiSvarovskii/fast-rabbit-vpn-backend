from typing import TYPE_CHECKING

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.consts import RefundStatus
from app.core.db.postgres import (
    Base, intpk, created_at, str_128
)


if TYPE_CHECKING:
    from app.core.models.users import User
    from app.core.models.payments import Payment


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[intpk]
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    telegram_charge_id: Mapped[str_128 | None]
    stars_amount: Mapped[int]
    rub_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, name="refund_status_enum", native_enum=False),
        default=RefundStatus.REQUESTED,
        comment="Статус операции возврата",
        nullable=False
    )
    error_message: Mapped[str | None]
    created_at: Mapped[created_at]
    processed_at: Mapped[datetime | None]
    payment: Mapped["Payment"] = relationship(back_populates="refunds")
    user: Mapped["User"] = relationship(back_populates="refunds")

    __table_args__ = (
        Index("ix_refunds_payment", "payment_id"),
        # опционально: ускоряет поиск по чеку
        Index("ix_refunds_charge", "telegram_charge_id"),
    )
