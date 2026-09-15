from redis import Redis

from .config import settings


class RedisHolder:
    """持有全局 Redis 客户端；测试时可替换为 fakeredis。"""

    def __init__(self):
        self._client: Redis | None = None

    def get(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(settings.redis_url, decode_responses=True)
        return self._client

    def set(self, client: Redis | None) -> None:
        self._client = client


redis_holder = RedisHolder()
