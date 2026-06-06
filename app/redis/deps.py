from typing import Annotated

from fastapi import Depends

from app.redis.client import redis_client
from app.redis.operations import RedisOps

RedisCache = RedisOps


def get_redis_ops() -> RedisOps:
    return RedisOps(redis_client.client)


RedisOpsDep = Annotated[RedisOps, Depends(get_redis_ops)]
RedisCacheDep = RedisOpsDep
