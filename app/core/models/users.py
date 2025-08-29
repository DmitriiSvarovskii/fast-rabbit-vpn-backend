from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy import BIGINT

from app.core.db.postgres import (
    Base, intpk, created_at
)

if TYPE_CHECKING:
    from app.core.models.wallet_ledger import WalletEntry
    from app.core.models.vpn_configs import VpnConfig
    from app.core.models.payments import Payment
    from app.core.models.refunds import Refund


class User(Base):
    __tablename__ = "users"

    id: Mapped[intpk]
    telegram_id: Mapped[int] = mapped_column(BIGINT, unique=True, index=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    username: Mapped[str | None]
    created_at: Mapped[created_at]

    payments: Mapped[list["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ledger: Mapped[list["WalletEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    vpn_configs: Mapped[list["VpnConfig"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="user", cascade="all, delete-orphan")
