from typing import Optional
from app.core.schemas.user import UserBase
from app.core.schemas.user_balance import UserBalanceBase
from app.core.schemas.key import KeyBase


class UserFullInfo(UserBase):
    balance: Optional[UserBalanceBase]
    keys: Optional[list[KeyBase]] = []
