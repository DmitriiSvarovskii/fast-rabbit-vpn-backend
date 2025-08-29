from pydantic_settings import SettingsConfigDict

from .base import BaseConfig


class DBSettings(BaseConfig):
    model_config = SettingsConfigDict(
        env_prefix='DB_',
    )

    HOST: str
    PORT: int
    NAME: str
    USER: str
    PASS: str

    @property
    def URL(self) -> str:
        return (f"postgresql+asyncpg://{self.USER}:{self.PASS}@"
                f"{self.HOST}:{self.PORT}/{self.NAME}")


db_settings = DBSettings()
