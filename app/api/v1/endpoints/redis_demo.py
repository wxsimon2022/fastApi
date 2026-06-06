from fastapi import APIRouter

from app.redis.deps import RedisOpsDep
from app.redis.examples import run_redis_examples
from app.schemas.common import ApiResponse, success
from app.schemas.redis import RedisSetBody

router = APIRouter(prefix="/redis", tags=["redis"])


# ------------------------------------------------------------------ #
# 基础 String 示例：GET / SET / DEL
# ------------------------------------------------------------------ #


@router.get("/{key}", response_model=ApiResponse[dict])
async def redis_get(key: str, redis: RedisOpsDep) -> ApiResponse[dict]:
    """GET key — 读取字符串。"""
    value = await redis.get(key)
    return success(data={"key": key, "value": value, "exists": value is not None})


@router.put("/{key}", response_model=ApiResponse[dict])
async def redis_set(
    key: str,
    body: RedisSetBody,
    redis: RedisOpsDep,
) -> ApiResponse[dict]:
    """SET key value [EX seconds] — 写入字符串，body.ttl 对应 EX。"""
    await redis.set(key, body.value, ttl=body.ttl)
    return success(
        data={"key": key, "value": body.value, "ttl": body.ttl},
        message="写入成功",
    )


@router.delete("/{key}", response_model=ApiResponse[dict])
async def redis_delete(key: str, redis: RedisOpsDep) -> ApiResponse[dict]:
    """DEL key — 删除键。"""
    deleted = await redis.delete(key)
    return success(data={"key": key, "deleted": deleted > 0}, message="删除成功")


# ------------------------------------------------------------------ #
# 一键跑通全部常用命令示例
# ------------------------------------------------------------------ #


@router.post("/examples/run", response_model=ApiResponse[dict])
async def redis_run_examples(redis: RedisOpsDep) -> ApiResponse[dict]:
    """
    依次演示 String / Key / Hash / List / Set / ZSet 常用命令。

    具体逻辑见 ``app/redis/examples.py``，每步均有中文注释。
    """
    results = await run_redis_examples(redis)
    return success(data=results, message="示例执行完成")
