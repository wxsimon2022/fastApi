from typing import Any, ClassVar

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select

from app.core.exceptions import AppException
from app.db.field_query import FieldQuery, FieldQueryExecutor
from app.db.serializers import row_to_dict
from app.schemas.pagination import PageResult


class BaseRepository:
    """
    通用数据访问基类。

    每个子类绑定一个 Model（一表一 Model，表名在 Model 上声明）::

        class UserRepository(BaseRepository):
            model = Users
    """

    model: ClassVar[type[DeclarativeBase]]
    pk_column: str = "id"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def _table(self):
        return self.model.__table__

    def _ensure_field(self, field: str) -> None:
        if field not in self._table.c:
            raise AppException(f"字段不存在: {field}", code=400)

    def _apply_filters(self, stmt: Select[Any], filters: dict[str, Any]) -> Select[Any]:
        for key, value in filters.items():
            if value is not None:
                self._ensure_field(key)
                stmt = stmt.where(self._table.c[key] == value)
        return stmt

    def by_field(self, field: str, value: Any) -> FieldQueryExecutor:
        return FieldQueryExecutor(self, field, value)

    async def query_field(
        self,
        query: FieldQuery,
    ) -> dict[str, Any] | PageResult[dict[str, Any]] | list[dict[str, Any]] | int | None:
        return await self.by_field(query.field, query.value).run(query)

    async def get_one(self, **filters: Any) -> dict[str, Any] | None:
        stmt = self._apply_filters(select(self._table), filters)
        row = (await self._session.execute(stmt)).mappings().first()
        return row_to_dict(row) if row else None

    async def get_one_by_id(self, record_id: int) -> dict[str, Any] | None:
        return await self.by_field(self.pk_column, record_id).one()

    async def get_one_by(self, field: str, value: Any) -> dict[str, Any] | None:
        return await self.by_field(field, value).one()

    async def get_id_by(self, field: str, value: Any) -> int | None:
        row = await self.get_one(**{field: value})
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
        return await self.by_field(field, value).all(limit=limit)

    async def get_list_by(
        self,
        field: str,
        value: Any,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> PageResult[dict[str, Any]]:
        return await self.by_field(field, value).page(page=page, page_size=page_size)

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

    async def update_by_id(
        self,
        record_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not data:
            raise AppException("无更新内容", code=400)
        if self.pk_column in data:
            raise AppException(f"不允许修改主键: {self.pk_column}", code=400)

        for key in data:
            self._ensure_field(key)

        stmt = (
            update(self._table)
            .where(self._table.c[self.pk_column] == record_id)
            .values(**data)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None

        await self._session.commit()
        return await self.get_one_by_id(record_id)
