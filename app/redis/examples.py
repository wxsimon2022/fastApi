"""
Redis 常用命令示例（带注释）。

可在脚本中调用::

    python scripts/test_redis.py

或在接口中调用 ``run_redis_examples(redis)`` 查看各命令效果。
"""

from typing import Any

from app.redis.operations import RedisOps

# 示例统一前缀，避免污染业务 key
_PREFIX = "demo:"


async def run_redis_examples(redis: RedisOps) -> dict[str, Any]:
    """依次演示 Redis 常用命令，返回每步执行结果。"""
    results: dict[str, Any] = {}

    # ==================== String 字符串 ====================
    key_str = f"{_PREFIX}string:hello"

    # SET / GET — 最基础的读写
    await redis.set(key_str, "world", ttl=60)
    results["string_get"] = await redis.get(key_str)

    # INCR — 计数器（浏览量、点赞数等）
    key_counter = f"{_PREFIX}string:counter"
    await redis.set(key_counter, "0")
    results["string_incr"] = await redis.incr(key_counter)

    # APPEND — 追加内容
    await redis.set(key_str, "hello")
    results["string_append_len"] = await redis.append(key_str, ", redis")

    # SET/GET JSON — 缓存对象
    key_json = f"{_PREFIX}string:user"
    await redis.set_json(key_json, {"id": 1, "name": "demo"}, ttl=60)
    results["string_json"] = await redis.get_json(key_json)

    # ==================== Key 键管理 ====================
    # EXISTS — 判断 key 是否存在
    results["key_exists"] = await redis.exists(key_str)

    # TTL — 查看剩余过期时间
    results["key_ttl"] = await redis.ttl(key_str)

    # EXPIRE — 动态续期
    await redis.expire(key_str, 120)
    results["key_ttl_after_expire"] = await redis.ttl(key_str)

    # PERSIST — 取消过期（变为永久 key）
    await redis.persist(key_str)
    results["key_ttl_after_persist"] = await redis.ttl(key_str)

    # ==================== Hash 哈希 ====================
    # 适合存储对象字段，如 user:1001 -> {name, age, role}
    key_hash = f"{_PREFIX}hash:user:1"

    # HSET / HGET — 单字段读写
    await redis.hset(key_hash, "name", "张三")
    results["hash_hget"] = await redis.hget(key_hash, "name")

    # HSET mapping — 批量写字段
    await redis.hmset(key_hash, {"age": "18", "role": "admin"})
    results["hash_hgetall"] = await redis.hgetall(key_hash)

    # HEXISTS / HDEL
    results["hash_hexists"] = await redis.hexists(key_hash, "role")
    results["hash_hdel"] = await redis.hdel(key_hash, "age")
    results["hash_after_hdel"] = await redis.hgetall(key_hash)

    # ==================== List 列表 ====================
    # 适合消息队列、最新 N 条记录
    key_list = f"{_PREFIX}list:msgs"

    # LPUSH / RPUSH — 两端入队
    await redis.delete(key_list)
    await redis.rpush(key_list, "msg1", "msg2")
    await redis.lpush(key_list, "msg0")
    results["list_lrange"] = await redis.lrange(key_list, 0, -1)

    # LPOP / RPOP — 两端出队
    results["list_lpop"] = await redis.lpop(key_list)
    results["list_rpop"] = await redis.rpop(key_list)
    results["list_llen"] = await redis.llen(key_list)

    # ==================== Set 集合 ====================
    # 适合标签、去重、共同好友
    key_set = f"{_PREFIX}set:tags"

    # SADD — 添加成员（自动去重）
    await redis.delete(key_set)
    results["set_sadd"] = await redis.sadd(key_set, "python", "redis", "python")
    results["set_smembers"] = sorted(await redis.smembers(key_set))

    # SISMEMBER — 判断是否存在
    results["set_sismember"] = await redis.sismember(key_set, "redis")

    # SREM — 移除成员
    results["set_srem"] = await redis.srem(key_set, "python")
    results["set_after_srem"] = sorted(await redis.smembers(key_set))

    # ==================== Sorted Set 有序集合 ====================
    # 适合排行榜（member=用户，score=分数）
    key_zset = f"{_PREFIX}zset:rank"

    # ZADD — 添加成员及分数
    await redis.delete(key_zset)
    results["zset_zadd"] = await redis.zadd(
        key_zset,
        {"user_a": 100, "user_b": 200, "user_c": 150},
    )

    # ZRANGE — 按分数升序取排名
    results["zset_zrange"] = await redis.zrange(key_zset, 0, -1, withscores=True)

    # ZSCORE — 查某个成员分数
    results["zset_zscore"] = await redis.zscore(key_zset, "user_b")

    # ZREM — 删除成员
    results["zset_zrem"] = await redis.zrem(key_zset, "user_a")
    results["zset_after_zrem"] = await redis.zrange(key_zset, 0, -1)

    # ==================== 清理示例 key ====================
    demo_keys = [
        key_str,
        key_counter,
        key_json,
        key_hash,
        key_list,
        key_set,
        key_zset,
    ]
    results["cleanup_deleted"] = await redis.delete(*demo_keys)

    return results
