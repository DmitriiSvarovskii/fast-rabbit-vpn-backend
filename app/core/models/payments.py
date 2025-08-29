from typing import TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String, Numeric, Enum, ForeignKey,
    Index, UniqueConstraint, func, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.consts import PaymentStatus
from app.core.db.postgres import (
    Base, intpk, created_at
)

if TYPE_CHECKING:
    from app.core.models.users import User
    from app.core.models.wallet_ledger import WalletEntry
    from app.core.models.refunds import Refund


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    payload: Mapped[str]
    stars_amount: Mapped[int]
    rub_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XTR", server_default=text("'XTR'"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", native_enum=False),
        default=PaymentStatus.PENDING,
        comment="Статус платежа",
        nullable=False
    )
    telegram_charge_id: Mapped[str | None] = mapped_column(comment="Telegram SuccessfulPayment.charge_id")
    created_at: Mapped[created_at]
    paid_at: Mapped[datetime | None]
    canceled_at: Mapped[datetime | None]
    failed_reason: Mapped[str | None]

    user: Mapped["User"] = relationship(back_populates="payments")
    ledger_entries: Mapped[list["WalletEntry"]] = relationship(back_populates="payment")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="payment", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("payload", name="uq_payments_payload"),
        # уникальный charge_id, если он есть (PostgreSQL partial unique index)
        Index(
            "uq_payments_charge_id_not_null",
            "telegram_charge_id",
            unique=True,
            postgresql_where=(func.coalesce(func.nullif("telegram_charge_id", ""), None) is not None)
        ),
        Index("ix_payments_user_status", "user_id", "status"),
        Index("ix_payments_created", "created_at"),
    )
