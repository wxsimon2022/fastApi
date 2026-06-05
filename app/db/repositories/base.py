from typing import Any

from sqlalchemy import Table, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.exceptions import AppException
from app.db.field_query import FieldQuery, FieldQueryExecutor
from app.db.serializers import row_to_dict
from app.schemas.pagination import PageResult


class BaseRepository:
    """
    通用数据访问基类。

    子类只需继承本类并绑定具体表，即可复用以下能力：
    - 按主键 / 多条件查单条：get_one_by_id、get_one
    - 分页列表：get_list
    - 按字段查询：by_field（链式）或 query_field（FieldQuery 对象）

    使用示例::

        class UserRepository(BaseRepository):
            pass

        # 主键查询
        user = await repo.get_one_by_id(1)

        # 分页
        page = await repo.get_list(page=1, page_size=10, status=1)

        # 按字段链式
        user = await repo.by_field("mobile", "13800138000").one()

        # 按字段统一对象
        result = await repo.query_field(
            FieldQuery.create(field="mobile", value="13800138000", mode="one")
        )
    """

    #: 主键列名，默认 ``id``。若表主键不同，在子类中覆盖。
    pk_column: str = "id"

    def __init__(self, session: AsyncSession, table: Table) -> None:
        """
        :param session: 当前请求的异步数据库 Session（由依赖注入提供）
        :param table: 已通过 Database 反射得到的 SQLAlchemy Table 对象
        """
        self._session = session
        self._table = table

    def _ensure_field(self, field: str) -> None:
        """校验字段是否存在于当前表，防止非法列名。"""
        if field not in self._table.c:
            raise AppException(f"字段不存在: {field}", code=400)

    def _apply_filters(self, stmt: Select[Any], filters: dict[str, Any]) -> Select[Any]:
        """
        为 SQL 语句追加等值过滤条件（AND）。

        ``value`` 为 ``None`` 的条件会被忽略，便于可选参数拼接。
        """
        for key, value in filters.items():
            if value is not None:
                self._ensure_field(key)
                stmt = stmt.where(self._table.c[key] == value)
        return stmt

    def by_field(self, field: str, value: Any) -> FieldQueryExecutor:
        """
        按单个字段发起查询，返回链式执行器。

        推荐用法::

            await repo.by_field("mobile", "13800138000").one()
            await repo.by_field("mobile", "13800138000").id()
            await repo.by_field("status", 1).page(page=1, page_size=10)
            await repo.by_field("status", 1).all(limit=50)
        """
        return FieldQueryExecutor(self, field, value)

    async def query_field(
        self,
        query: FieldQuery,
    ) -> dict[str, Any] | PageResult[dict[str, Any]] | list[dict[str, Any]] | int | None:
        """
        根据 ``FieldQuery`` 统一执行按字段查询。

        ``query.mode`` 决定返回类型：
        - ``one``  → ``dict | None``
        - ``id``   → ``int | None``
        - ``list`` → ``PageResult``
        - ``all``  → ``list[dict]``
        """
        return await self.by_field(query.field, query.value).run(query)

    async def get_one(self, **filters: Any) -> dict[str, Any] | None:
        """
        按一个或多个等值条件查单条记录。

        多条件之间为 AND 关系；无匹配时返回 ``None``。

        示例::

            await repo.get_one(id=1)
            await repo.get_one(mobile="13800138000", status=1)
        """
        stmt = self._apply_filters(select(self._table), filters)
        row = (await self._session.execute(stmt)).mappings().first()
        return row_to_dict(row) if row else None

    async def get_one_by_id(self, record_id: int) -> dict[str, Any] | None:
        """按主键查单条，等价于 ``get_one(id=record_id)``。"""
        return await self.by_field(self.pk_column, record_id).one()

    async def get_one_by(self, field: str, value: Any) -> dict[str, Any] | None:
        """按指定字段查单条，等价于 ``by_field(field, value).one()``。"""
        return await self.by_field(field, value).one()

    async def get_id_by(self, field: str, value: Any) -> int | None:
        """
        按指定字段查主键值。

        仅返回 ``pk_column`` 对应的 id，不返回完整行。
        """
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
        """
        按字段查列表（不分页）。

        结果最多返回 ``limit`` 条，适用于下拉选项等小数据量场景。
        """
        return await self.by_field(field, value).all(limit=limit)

    async def get_list_by(
        self,
        field: str,
        value: Any,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> PageResult[dict[str, Any]]:
        """按字段分页查列表，等价于 ``by_field(field, value).page(...)``。"""
        return await self.by_field(field, value).page(page=page, page_size=page_size)

    async def get_list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        **filters: Any,
    ) -> PageResult[dict[str, Any]]:
        """
        分页查询列表，支持多字段等值过滤。

        :param page: 页码，从 1 开始
        :param page_size: 每页条数
        :param filters: 可选等值条件，如 ``status=1, role="admin"``

        返回 ``PageResult``，包含 ``items``、``total``、``page``、``page_size``、``pages``。
        """
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
        """
        按主键更新记录，仅更新 ``data`` 中包含的字段。

        :param record_id: 主键值
        :param data: 待更新字段，如 ``{"username": "tom", "is_admin": 0}``
        :return: 更新后的完整记录；记录不存在时返回 ``None``
        """
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
