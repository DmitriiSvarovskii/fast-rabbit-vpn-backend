from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship, mapped_column
from datetime import datetime
from sqlalchemy import (
    ForeignKey, Index, UniqueConstraint, text
)
from app.core.db.postgres import (
    Base, intpk, str_256, str_64, str_128, created_at,
)

if TYPE_CHECKING:
    from app.core.models.users import User


class VpnConfig(Base):
    __tablename__ = "vpn_configs"

    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    uuid: Mapped[str_64 | None] = mapped_column(comment="UUID пользователя в провайдере VPN")
    vpn_domain: Mapped[str_64 | None]
    flow: Mapped[str_64 | None]
    email: Mapped[str_64 | None]

    country: Mapped[str_64 | None]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    created_at: Mapped[created_at]
    deleted_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="vpn_configs")

    __table_args__ = (
        UniqueConstraint("user_id", "uuid", name="uq_vpn_config_user_external"),
        Index("ix_vpn_configs_created", "created_at"),
    )
