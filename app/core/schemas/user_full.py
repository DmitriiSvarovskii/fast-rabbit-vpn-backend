from typing import Optional
from app.core.schemas.user import UserBase
from app.core.schemas.user_balance import UserBalanceBase
from app.core.schemas.key import KeyBase
from pydantic import BaseModel, ConfigDict

JWT_TTL = 3600


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_TTL


class UserFullInfo(UserBase):
    balance: Optional[UserBalanceBase]
    keys: Optional[list[KeyBase]] = []
    access_token: Optional[TokenResponse] = None
