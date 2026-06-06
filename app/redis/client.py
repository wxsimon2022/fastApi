from redis.asyncio import Redis


class RedisClient:
    """Redis 异步客户端组件。"""

    def __init__(self) -> None:
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis 未初始化，请先调用 redis_client.startup()")
        return self._client

    async def startup(self, url: str) -> None:
        self._client = Redis.from_url(url, decode_responses=True)
        await self._client.ping()

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None


redis_client = RedisClient()
