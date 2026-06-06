from typing import Annotated, Literal

from fastapi import Depends, Query


def parse_columns(fields: str | None) -> list[str] | None:
    """解析 fields=id,username 为列名列表。"""
    if not fields:
        return None
    columns = [item.strip() for item in fields.split(",") if item.strip()]
    return columns or None


class ColumnsParams:
    """指定查询返回字段。"""

    def __init__(
        self,
        fields: str | None = Query(
            None,
            description="返回字段，逗号分隔，如 id,username,is_admin；不传则返回全部字段",
        ),
    ) -> None:
        self.columns = parse_columns(fields)


ColumnsQuery = Annotated[ColumnsParams, Depends()]


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(10, ge=1, le=100, description="每页条数，最大 100"),
    ) -> None:
        self.page = page
        self.page_size = page_size


PageParams = Annotated[PaginationParams, Depends()]


class FieldLookupParams:
    """按字段查询参数。"""

    def __init__(
        self,
        field: str = Query(..., min_length=1, description="字段名，如 mobile、username"),
        value: str = Query(..., min_length=1, description="字段值"),
        lookup_type: Literal["one", "list", "id"] = Query(
            "one",
            alias="type",
            description="one=单条, list=分页列表, id=仅返回主键",
        ),
    ) -> None:
        self.field = field
        self.value = value
        self.lookup_type = lookup_type


FieldParams = Annotated[FieldLookupParams, Depends()]


def build_field_query(
    lookup: FieldLookupParams,
    pagination: PaginationParams,
) -> "FieldQuery":
    from app.db.field_query import FieldQuery

    return FieldQuery.create(
        field=lookup.field,
        value=lookup.value,
        mode=lookup.lookup_type,
        page=pagination.page,
        page_size=pagination.page_size,
    )


