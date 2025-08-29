from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
