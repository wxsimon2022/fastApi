from typing import Any

from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.exceptions import AppException
from app.db.serializers import row_to_dict
from app.schemas.pagination import PageResult


class BaseRepository:
    """通用数据访问基类。"""

    pk_column: str = "id"

    def __init__(self, session: AsyncSession, table: Table) -> None:
        self._session = session
        self._table = table

    def _ensure_field(self, field: str) -> None:
        if field not in self._table.c:
            raise AppException(f"字段不存在: {field}", code=400)

    def _apply_filters(self, stmt: Select[Any], filters: dict[str, Any]) -> Select[Any]:
        for key, value in filters.items():
            if value is not None:
                self._ensure_field(key)
                stmt = stmt.where(self._table.c[key] == value)
        return stmt

    async def get_one(self, **filters: Any) -> dict[str, Any] | None:
        stmt = self._apply_filters(select(self._table), filters)
        row = (await self._session.execute(stmt)).mappings().first()
        return row_to_dict(row) if row else None

    async def get_one_by_id(self, record_id: int) -> dict[str, Any] | None:
        return await self.get_one_by(self.pk_column, record_id)

    async def get_one_by(self, field: str, value: Any) -> dict[str, Any] | None:
        """按指定字段查单条。"""
        return await self.get_one(**{field: value})

    async def get_id_by(self, field: str, value: Any) -> int | None:
        """按指定字段查主键 id。"""
        row = await self.get_one_by(field, value)
        if row is None:
            return None
        pk = row.get(self.pk_column)
        return int(pk) if pk is not None else None

    async def get_all_by(
        self,
        field: str,
        value: Any,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """按指定字段查列表（不分页，带上限）。"""
        self._ensure_field(field)
        stmt = self._apply_filters(select(self._table), {field: value}).limit(limit)
        rows = (await self._session.execute(stmt)).mappings().all()
        return [row_to_dict(row) for row in rows]

    async def get_list_by(
        self,
        field: str,
        value: Any,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> PageResult[dict[str, Any]]:
        """按指定字段分页查列表。"""
        return await self.get_list(page=page, page_size=page_size, **{field: value})

    async def get_list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        **filters: Any,
    ) -> PageResult[dict[str, Any]]:
        count_stmt = self._apply_filters(
            select(func.count()).select_from(self._table),
            filters,
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        list_stmt = self._apply_filters(select(self._table), filters)
        list_stmt = list_stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(list_stmt)).mappings().all()

        pages = (total + page_size - 1) // page_size if page_size else 0
        return PageResult(
            items=[row_to_dict(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
