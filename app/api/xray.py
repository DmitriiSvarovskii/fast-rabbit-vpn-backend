import logging

from fastapi import APIRouter, status

from app.core.schemas.xray import XraySchemasCreate
from app.utils.xray import XrayService

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
        service = XrayService()
        await service.reload()
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
    user_data: XraySchemasCreate
):
    try:
        service = XrayService()
        await service.add_user(user_data=user_data)
        return {"message": "Xray reloaded"}
    except Exception as e:
        logger.error(e)
        return {"message": "Xray reload failed"}


@router.delete(
    "/delete-user/{user_id}",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_user_xray_service(
    user_id: str
):
    try:
        service = XrayService()
        await service.delete_user(user_id=user_id)
        return {"message": "Xray reloaded"}
    except Exception as e:
        logger.error(e)
        return {"message": "Xray reload failed"}
