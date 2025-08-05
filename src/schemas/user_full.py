from typing import Optional
from src.schemas.user import UserBase
from src.schemas.user_balance import UserBalanceBase
from src.schemas.key import KeyBase


class UserFullInfo(UserBase):
    balance: Optional[UserBalanceBase]
    keys: Optional[list[KeyBase]] = []
