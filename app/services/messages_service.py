"""c_messages 业务逻辑。"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AppException
from app.db.field_query import FieldQuery, FieldQueryMode
from app.db.repositories.messages import MessageRepository
from app.schemas.pagination import PageResult


class MessageService:
    """Messages 模块业务逻辑。"""

    def __init__(self, *, repo: MessageRepository) -> None:
        self._repo = repo

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
        return await self._repo.get_all(columns=MessageRepository.ALL_LIST_COLUMNS)

    async def lookup(self, query: FieldQuery) -> Any:
        result = await self._repo.query_field(query)
        if query.mode == FieldQueryMode.ONE:
            if result is None:
                raise AppException("记录不存在", code=404)
            return result
        if query.mode == FieldQueryMode.ID:
            if result is None:
                raise AppException("记录不存在", code=404)
            return {"id": result}
        if query.mode in (FieldQueryMode.LIST, FieldQueryMode.ALL):
            return result
        raise AppException(f"不支持的查询类型: {query.mode}", code=400)

    async def get_by_id(
        self,
        record_id: int,
        *,
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        item = await self._repo.get_one_by_id(record_id, columns=columns)
        if item is None:
            raise AppException("记录不存在", code=404)
        return item

    async def update(self, record_id: int, data: dict[str, Any]) -> dict[str, Any]:
        item = await self._repo.update_by_id(record_id, data)
        if item is None:
            raise AppException("记录不存在", code=404)
        return item
