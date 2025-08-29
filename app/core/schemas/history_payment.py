from pydantic import BaseModel, ConfigDict


class HistoryPaymentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    amount: float
    created_at: str
