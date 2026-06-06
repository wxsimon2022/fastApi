"""用户查询、更新、缓存等业务逻辑。"""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.field_query import FieldQuery, FieldQueryMode
from app.db.repositories.user import UserRepository
from app.redis.keys import user_cache_key
from app.redis.operations import RedisOps
from app.schemas.pagination import PageResult

logger = get_logger(__name__)


class UserService:
    """用户模块业务逻辑。"""

    def __init__(
        self,
        *,
        repo: UserRepository,
        cache: RedisOps,
        settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._cache = cache
        self._settings = settings or get_settings()

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        columns: list[str] | None = None,
    ) -> PageResult[dict[str, Any]]:
        return await self._repo.get_list(
            page=page,
            page_size=page_size,
            columns=columns,
        )

    async def list_all(self) -> list[dict[str, Any]]:
        logger.info("查询全部用户列表（不分页）")
        return await self._repo.get_all(columns=UserRepository.ALL_LIST_COLUMNS)

    async def lookup(self, query: FieldQuery) -> Any:
        """按字段查询，返回单条 / id / 分页列表等。"""
        result = await self._repo.query_field(query)

        if query.mode == FieldQueryMode.ONE:
            if result is None:
                logger.error("用户不存在，username: %s", query.value)
                raise AppException("用户不存在", code=404)
            return result
        if query.mode == FieldQueryMode.ID:
            if result is None:
                logger.error("用户不存在，id: %s", query.value)
                raise AppException("用户不存在", code=404)
            return {"id": result}
        if query.mode in (FieldQueryMode.LIST, FieldQueryMode.ALL):
            return result

        raise AppException(f"不支持的查询类型: {query.mode}", code=400)

    async def get_by_id(
        self,
        user_id: int,
        *,
        columns: list[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """
        按 id 查询用户。

        返回 (用户数据, message)；全字段查询时走 Redis 缓存。
        """
        if columns is None:
            key = user_cache_key(user_id)
            cached = await self._cache.get_json(key)
            if cached is not None:
                return cached, "ok(cache)"

            user = await self._repo.get_one_by_id(user_id)
            if user is None:
                raise AppException("用户不存在", code=404)

            await self._cache.set_json(
                key,
                user,
                ttl=self._settings.redis_cache_ttl,
            )
            return user, "ok"

        user = await self._repo.get_one_by_id(user_id, columns=columns)
        if user is None:
            raise AppException("用户不存在", code=404)
        return user, "ok"

    async def update(self, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """更新用户并清除缓存。"""
        user = await self._repo.update_by_id(user_id, data)
        if user is None:
            raise AppException("用户不存在", code=404)

        await self._cache.delete(user_cache_key(user_id))
        return user
