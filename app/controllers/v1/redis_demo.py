from fastapi import APIRouter

from app.redis.deps import RedisOpsDep
from app.redis.examples import run_redis_examples
from app.schemas.common import ApiResponse, success
from app.schemas.redis import RedisSetBody

router = APIRouter(prefix="/redis", tags=["redis"])


@router.get("/{key}", response_model=ApiResponse[dict])
async def redis_get(key: str, redis: RedisOpsDep) -> ApiResponse[dict]:
    value = await redis.get(key)
    return success(data={"key": key, "value": value, "exists": value is not None})


@router.put("/{key}", response_model=ApiResponse[dict])
async def redis_set(
    key: str,
    body: RedisSetBody,
    redis: RedisOpsDep,
) -> ApiResponse[dict]:
    await redis.set(key, body.value, ttl=body.ttl)
    return success(
        data={"key": key, "value": body.value, "ttl": body.ttl},
        message="写入成功",
    )


@router.delete("/{key}", response_model=ApiResponse[dict])
async def redis_delete(key: str, redis: RedisOpsDep) -> ApiResponse[dict]:
    deleted = await redis.delete(key)
    return success(data={"key": key, "deleted": deleted > 0}, message="删除成功")


@router.post("/examples/run", response_model=ApiResponse[dict])
async def redis_run_examples(redis: RedisOpsDep) -> ApiResponse[dict]:
    results = await run_redis_examples(redis)
    return success(data=results, message="示例执行完成")
