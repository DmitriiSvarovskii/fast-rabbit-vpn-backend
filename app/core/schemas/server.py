from pydantic import BaseModel, ConfigDict


class ServerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    country: str


class ServerCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
