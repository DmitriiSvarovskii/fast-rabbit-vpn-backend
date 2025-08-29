import datetime
from typing import Annotated, AsyncGenerator, Any
from sqlalchemy import MetaData, String, text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, mapped_column
from sqlalchemy.pool import NullPool
from app.core.configs.db import db_settings as settings


metadata = MetaData()


engine = create_async_engine(settings.URL, poolclass=NullPool)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


str_64 = Annotated[str, 64]
str_128 = Annotated[str, 128]
str_256 = Annotated[str, 256]
str_4048 = Annotated[str, 4048]


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSON,
        str_64: String(64),
        str_128: String(128),
        str_256: String(256),
        str_4048: String(4048),

    }


intpk = Annotated[int, mapped_column(primary_key=True, index=True)]

is_active = Annotated[bool, mapped_column(server_default=text("true"))]

created_at = Annotated[datetime.datetime, mapped_column(
    default=func.now())]

changed_at = Annotated[datetime.datetime, mapped_column(
    default=func.now())]

created_by = Annotated[int, mapped_column(
    ForeignKey("employees.id", ondelete="CASCADE"))]

updated_at = Annotated[datetime.datetime,
                       mapped_column(server_onupdate=func.now())]

updated_by = Annotated[int, mapped_column(
    ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)]

changed_by = Annotated[int, mapped_column(
    ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)]

deleted_at = Annotated[datetime.datetime, mapped_column(
    server_default=func.now(), nullable=True)]

is_deleted = Annotated[bool, mapped_column(server_default=text("false"))]

deleted_by = Annotated[int, mapped_column(
    ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)]
