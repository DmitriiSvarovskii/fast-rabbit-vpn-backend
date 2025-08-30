from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.db.postgres import get_async_session
from app.core.models.users import User
from app.core.models.wallet_ledger import WalletEntry
from app.core.models.vpn_configs import VpnConfig
from app.core.schemas.user_full import UserFullInfo
from app.core.schemas.user_balance import UserBalanceBase
from app.core.schemas.key import KeyBase
from app.core.configs.vpn_config import vpn_settings
from datetime import datetime

router = APIRouter(prefix="/user", tags=["User"])


def build_vless_link(cfg: VpnConfig) -> str:
    return (
        f"vless://{cfg.uuid}@{cfg.vpn_domain}:443"
        f"?flow={cfg.flow or 'xtls-rprx-vision'}&type=tcp&security=reality"
        f"&fp=random&sni={vpn_settings.SNI}&pbk={vpn_settings.PBK}"
        f"&sid={vpn_settings.SID}&spx=/#" + (cfg.email or "vpn-user")
    )


def dt_to_str(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


@router.get(
    "/{telegram_id}",
    response_model=UserFullInfo,
    status_code=status.HTTP_200_OK,
)
async def get_user_full_info(
    telegram_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    # 1. Пользователь
    user = (
        await db.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(404, detail="User not found")

    # 2. Баланс
    balance = (
        await db.execute(
            select(func.coalesce(func.sum(WalletEntry.amount_rub), 0))
            .where(WalletEntry.user_id == user.id)
        )
    ).scalar_one()

    # 3. VPN-конфиги
    configs = (
        await db.execute(
            select(VpnConfig)
            .where(VpnConfig.user_id == user.id, VpnConfig.is_active.is_(True))
        )
    ).scalars().all()

    return UserFullInfo(
        id=user.id,
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        balance=UserBalanceBase(balance=float(balance)),
        keys=[
            KeyBase(
                id=cfg.id,
                key=build_vless_link(cfg),         # ✅ готовая vless-ссылка
                server=cfg.vpn_domain,
                country=cfg.country,
                created_at=dt_to_str(cfg.created_at),
            )
            for cfg in configs
        ],
    )

# import logging

# from fastapi import APIRouter, status

# from app.core.schemas.user_full import UserFullInfo
# from app.core.schemas.user_balance import UserBalanceBase
# from app.core.schemas.key import KeyBase
# from app.test_data import user_data

# logger = logging.getLogger(__name__)

# router = APIRouter(
#     prefix="/user",
#     tags=["User"]
# )


# @router.get(
#     "/{id}",
#     response_model=UserFullInfo,
#     status_code=status.HTTP_200_OK,
# )
# async def get_user_full_info(id: int):
#     return UserFullInfo(
#         id=user_data["id"],
#         telegram_id=id,
#         first_name=user_data.get("first_name"),
#         last_name=user_data.get("last_name"),
#         username=user_data.get("username"),
#         balance=UserBalanceBase(balance=user_data["balance"]),
#         keys=[KeyBase(**k) for k in user_data["keys"]],
#     )
