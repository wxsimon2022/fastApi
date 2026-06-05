from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from app.schemas.pagination import PageResult

if TYPE_CHECKING:
    from app.db.repositories.base import BaseRepository


class FieldQueryMode(StrEnum):
    ONE = "one"
    LIST = "list"
    ID = "id"
    ALL = "all"


@dataclass(slots=True)
class FieldQuery:
    """按字段查询的统一入参。"""

    field: str
    value: Any
    mode: FieldQueryMode = FieldQueryMode.ONE
    page: int = 1
    page_size: int = 10
    limit: int = 100

    @classmethod
    def create(
        cls,
        *,
        field: str,
        value: Any,
        mode: str = "one",
        page: int = 1,
        page_size: int = 10,
        limit: int = 100,
    ) -> "FieldQuery":
        return cls(
            field=field,
            value=value,
            mode=FieldQueryMode(mode),
            page=page,
            page_size=page_size,
            limit=limit,
        )


class FieldQueryExecutor:
    """按字段查询执行器。"""

    def __init__(self, repo: "BaseRepository", field: str, value: Any) -> None:
        self._repo = repo
        self._field = field
        self._value = value

    async def one(self) -> dict[str, Any] | None:
        return await self._repo.get_one(**{self._field: self._value})

    async def id(self) -> int | None:
        row = await self.one()
        if row is None:
            return None
        pk = row.get(self._repo.pk_column)
        return int(pk) if pk is not None else None

    async def page(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> PageResult[dict[str, Any]]:
        return await self._repo.get_list(
            page=page,
            page_size=page_size,
            **{self._field: self._value},
        )

    async def all(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return await self._repo.get_all_by(self._field, self._value, limit=limit)

    async def run(
        self,
        query: FieldQuery,
    ) -> dict[str, Any] | PageResult[dict[str, Any]] | list[dict[str, Any]] | int | None:
        if query.mode == FieldQueryMode.ONE:
            return await self.one()
        if query.mode == FieldQueryMode.ID:
            return await self.id()
        if query.mode == FieldQueryMode.LIST:
            return await self.page(page=query.page, page_size=query.page_size)
        if query.mode == FieldQueryMode.ALL:
            return await self.all(limit=query.limit)
        raise ValueError(f"unsupported mode: {query.mode}")
