import logging

from fastapi import APIRouter, status

from src.schemas.payment import PaymentBase, PaymentTest
from src.schemas.history_payment import HistoryPaymentBase
from src.test_data import user_data

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payment",
    tags=["Payment"]
)


@router.post(
    "/",
    response_model=PaymentTest,
    status_code=status.HTTP_200_OK,
)
async def reload_xray_service(data: PaymentBase):
    user_data["balance"] += data.amount
    return PaymentTest(balance=user_data["balance"])


@router.get(
    "/{user_id}",
    response_model=list[HistoryPaymentBase],
    status_code=status.HTTP_200_OK,
)
async def get_payment_history(user_id: int):
    return [
        HistoryPaymentBase(id=1, user_id=user_id, amount=100.0,
                           created_at="2023-10-01T12:00:00Z"),
        HistoryPaymentBase(id=2, user_id=user_id, amount=150.0,
                           created_at="2023-11-15T09:30:00Z"),
    ]
