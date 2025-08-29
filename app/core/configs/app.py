from .base import BaseConfig


class AppSettings(BaseConfig):
    DEBUG: bool

    SERVICE_HOST: str
    SERVICE_PORT: int

    ALLOW_METHODS: list[str]
    ALLOW_HOSTS: list[str]
    ALLOW_HEADERS: list[str]
    ALLOW_ORIGINS: list[str]
    ALLOW_CREDENTIALS: bool


app_settings = AppSettings()
