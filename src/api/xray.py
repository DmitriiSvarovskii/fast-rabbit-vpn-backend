import logging

from fastapi import APIRouter, status

from src.schemas.vpn_config import XrayConfigCreate
from src.utils.xray import XrayService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/xray",
    tags=["Xray"]
)


@router.post(
    "/reload",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def reload_xray_service():
    try:
        await XrayService.reload()
        return {"message": "Xray reloaded"}
    except Exception as e:
        logger.error(e)
        return {"message": "Xray reload failed"}


@router.post(
    "/add-user",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def add_user_xray_service(
    user_data: XrayConfigCreate
):
    try:
        await XrayService.add_user()
        return {"message": "Xray reloaded"}
    except Exception as e:
        logger.error(e)
        return {"message": "Xray reload failed"}


@router.delete(
    "/delete-user",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_user_xray_service(
    user_data: XrayConfigCreate
):
    try:
        await XrayService.delete_user()
        return {"message": "Xray reloaded"}
    except Exception as e:
        logger.error(e)
        return {"message": "Xray reload failed"}
