import logging
import redis.asyncio as aioredis

from app.core.configs import redis_settings

logger = logging.getLogger(__name__)


class RedisClient:
    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """
        Получить клиента Redis.

        Логи:
          - INFO при попытке подключения
          - ERROR при неудаче
        """
        try:
            logger.info("Подключение к Redis: %s", redis_settings.URL)
            client = aioredis.from_url(
                redis_settings.URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            logger.info("Успешно подключились к Redis")
            return client
        except Exception:
            logger.exception("Не удалось подключиться к Redis", exc_info=True)
            raise


redis_client = RedisClient()
