from .base import BaseConfig


class BotSettings(BaseConfig):
    BOT_TOKEN: str
    BOT_ID: int


bot_settings = BotSettings()
