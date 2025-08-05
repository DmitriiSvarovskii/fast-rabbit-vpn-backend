import logging

from fastapi import APIRouter, status

from src.schemas.key import KeyCreate
from src.test_data import user_data, server_data

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/key",
    tags=["Key"]
)


def get_server_by_id(server_id: int):
    return next((s for s in server_data if s["id"] == server_id), None)


@router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def create_server(data: KeyCreate):
    server_info = get_server_by_id(data.server_id)
    user_data["keys"].append({
        "id": 4,
        "country": server_info["country"],
        "key": f"vless://new-key-value/{server_info["country"]}",
        "created_at": "2025-08-04T20:00:00Z"
    })
    return {"id": 4}


@router.delete(
    "/",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def delete_server(server_id: int):
    user_data["keys"] = [k for k in user_data["keys"] if k["id"] != server_id]
    return {"status": "sucsses"}
