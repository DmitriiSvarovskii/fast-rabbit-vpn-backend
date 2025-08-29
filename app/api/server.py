import logging

from fastapi import APIRouter, status

from app.core.schemas.server import ServerBase
from app.test_data import server_data

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/server",
    tags=["Server"]
)


@router.get(
    "/",
    response_model=list[ServerBase],
    status_code=status.HTTP_200_OK,
)
async def get_payment_history():
    return [ServerBase(**k) for k in server_data]
