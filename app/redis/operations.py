from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class RedisOps:
    """
    Redis 常用命令异步封装。

    方法名与 Redis 命令对应，可直接在业务代码中注入 ``RedisOpsDep`` 使用。
    """

    def __init__(self, client: Redis) -> None:
        self._client = client

    # ------------------------------------------------------------------ #
    # String 字符串
    # ------------------------------------------------------------------ #

    async def get(self, key: str) -> str | None:
        """GET key — 获取字符串值，不存在返回 None。"""
        return await self._client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ttl: int | None = None,
    ) -> None:
        """SET key value / SETEX key seconds value — 写入字符串，可选过期时间（秒）。"""
        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    async def incr(self, key: str, amount: int = 1) -> int:
        """INCR / INCRBY key increment — 自增，返回递增后的值。"""
        if amount == 1:
            return await self._client.incr(key)
        return await self._client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """DECR / DECRBY key decrement — 自减，返回递减后的值。"""
        if amount == 1:
            return await self._client.decr(key)
        return await self._client.decrby(key, amount)

    async def append(self, key: str, value: str) -> int:
        """APPEND key value — 追加字符串，返回追加后总长度。"""
        return await self._client.append(key, value)

    async def get_json(self, key: str) -> Any | None:
        """GET + JSON 反序列化 — 适合缓存 dict/list。"""
        raw = await self.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        """SET + JSON 序列化 — 适合缓存 dict/list。"""
        await self.set(
            key,
            json.dumps(value, ensure_ascii=False, default=str),
            ttl=ttl,
        )

    # ------------------------------------------------------------------ #
    # Key 键管理
    # ------------------------------------------------------------------ #

    async def delete(self, *keys: str) -> int:
        """DEL key [key ...] — 删除一个或多个键，返回删除数量。"""
        if not keys:
            return 0
        return await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """EXISTS key — 判断键是否存在。"""
        return bool(await self._client.exists(key))

    async def expire(self, key: str, seconds: int) -> bool:
        """EXPIRE key seconds — 设置过期时间（秒）。"""
        return bool(await self._client.expire(key, seconds))

    async def ttl(self, key: str) -> int:
        """
        TTL key — 查询剩余过期秒数。

        - 正数：剩余秒数
        - -1：永久有效
        - -2：键不存在
        """
        return await self._client.ttl(key)

    async def persist(self, key: str) -> bool:
        """PERSIST key — 移除过期时间，使键永久有效。"""
        return bool(await self._client.persist(key))

    # ------------------------------------------------------------------ #
    # Hash 哈希
    # ------------------------------------------------------------------ #

    async def hget(self, name: str, field: str) -> str | None:
        """HGET name field — 获取哈希单个字段。"""
        return await self._client.hget(name, field)

    async def hset(self, name: str, field: str, value: str) -> int:
        """HSET name field value — 设置哈希单个字段，返回新增字段数。"""
        return await self._client.hset(name, field, value)

    async def hmset(self, name: str, mapping: dict[str, str]) -> int:
        """HSET name mapping — 批量设置哈希字段（Redis 4+ 推荐写法）。"""
        return await self._client.hset(name, mapping=mapping)

    async def hgetall(self, name: str) -> dict[str, str]:
        """HGETALL name — 获取哈希全部字段。"""
        return await self._client.hgetall(name)

    async def hdel(self, name: str, *fields: str) -> int:
        """HDEL name field [field ...] — 删除哈希字段，返回删除数量。"""
        return await self._client.hdel(name, *fields)

    async def hexists(self, name: str, field: str) -> bool:
        """HEXISTS name field — 判断哈希字段是否存在。"""
        return bool(await self._client.hexists(name, field))

    # ------------------------------------------------------------------ #
    # List 列表
    # ------------------------------------------------------------------ #

    async def lpush(self, name: str, *values: str) -> int:
        """LPUSH name element [element ...] — 左侧入队，返回列表长度。"""
        return await self._client.lpush(name, *values)

    async def rpush(self, name: str, *values: str) -> int:
        """RPUSH name element [element ...] — 右侧入队，返回列表长度。"""
        return await self._client.rpush(name, *values)

    async def lrange(self, name: str, start: int, end: int) -> list[str]:
        """LRANGE name start stop — 按索引区间取列表元素（0 为头，-1 为尾）。"""
        return await self._client.lrange(name, start, end)

    async def lpop(self, name: str) -> str | None:
        """LPOP name — 左侧出队。"""
        return await self._client.lpop(name)

    async def rpop(self, name: str) -> str | None:
        """RPOP name — 右侧出队。"""
        return await self._client.rpop(name)

    async def llen(self, name: str) -> int:
        """LLEN name — 列表长度。"""
        return await self._client.llen(name)

    # ------------------------------------------------------------------ #
    # Set 集合
    # ------------------------------------------------------------------ #

    async def sadd(self, name: str, *values: str) -> int:
        """SADD name member [member ...] — 添加成员，返回新增数量。"""
        return await self._client.sadd(name, *values)

    async def smembers(self, name: str) -> set[str]:
        """SMEMBERS name — 获取全部成员。"""
        return await self._client.smembers(name)

    async def sismember(self, name: str, value: str) -> bool:
        """SISMEMBER name member — 判断成员是否存在。"""
        return bool(await self._client.sismember(name, value))

    async def srem(self, name: str, *values: str) -> int:
        """SREM name member [member ...] — 移除成员，返回删除数量。"""
        return await self._client.srem(name, *values)

    # ------------------------------------------------------------------ #
    # Sorted Set 有序集合
    # ------------------------------------------------------------------ #

    async def zadd(self, name: str, mapping: dict[str, float]) -> int:
        """ZADD name score member [score member ...] — 添加成员及分数。"""
        return await self._client.zadd(name, mapping)

    async def zrange(
        self,
        name: str,
        start: int,
        end: int,
        *,
        withscores: bool = False,
    ) -> list[Any]:
        """ZRANGE name start stop [WITHSCORES] — 按排名区间取成员。"""
        return await self._client.zrange(name, start, end, withscores=withscores)

    async def zscore(self, name: str, member: str) -> float | None:
        """ZSCORE name member — 获取成员分数。"""
        return await self._client.zscore(name, member)

    async def zrem(self, name: str, *members: str) -> int:
        """ZREM name member [member ...] — 删除成员，返回删除数量。"""
        return await self._client.zrem(name, *members)

