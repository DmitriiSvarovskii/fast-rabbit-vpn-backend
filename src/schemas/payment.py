from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    amount: float


class PaymentTest(BaseModel):
    balance: float
