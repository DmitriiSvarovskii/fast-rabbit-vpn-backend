from typing import TYPE_CHECKING
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Numeric, Enum, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.consts import LedgerType
from app.core.db.postgres import (
    Base, intpk, created_at
)


if TYPE_CHECKING:
    from app.core.models.users import User
    from app.core.models.payments import Payment


class WalletEntry(Base):
    __tablename__ = "wallet_ledger"

    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), index=True)

    entry_type: Mapped[LedgerType] = mapped_column(
        Enum(LedgerType, name="ledger_type_enum", native_enum=False),
        comment="Тип операции",
        nullable=False
    )
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # >0 пополнение; <0 списание
    comment: Mapped[str | None]

    created_at: Mapped[created_at]

    user: Mapped["User"] = relationship(back_populates="ledger")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="ledger_entries")

    __table_args__ = (
        Index("ix_wallet_ledger_user_created", "user_id", "created_at"),
    )
