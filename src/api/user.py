import logging

from fastapi import APIRouter, status

from src.schemas.user_full import UserFullInfo
from src.schemas.user_balance import UserBalanceBase
from src.schemas.key import KeyBase
from src.test_data import user_data

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user",
    tags=["User"]
)


@router.get(
    "/{id}",
    response_model=UserFullInfo,
    status_code=status.HTTP_200_OK,
)
async def get_user_full_info(id: int):
    return UserFullInfo(
        id=user_data["id"],
        telegram_id=user_data["telegram_id"],
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        balance=UserBalanceBase(balance=user_data["balance"]),
        keys=[KeyBase(**k) for k in user_data["keys"]],
    )
