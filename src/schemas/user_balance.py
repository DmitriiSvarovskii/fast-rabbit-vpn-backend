from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserBalanceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    balance: Optional[float] = None
