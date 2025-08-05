from pydantic import BaseModel, ConfigDict


class KeyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    country: str
    key: str
    created_at: str


class KeyCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    server_id: int
