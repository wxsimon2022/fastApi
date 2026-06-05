from typing import Any, TypeVar

from app.core.exceptions import AppException
from app.db.field_query import FieldQuery, FieldQueryMode
from app.db.repositories.base import BaseRepository
from app.schemas.common import ApiResponse, success
from app.schemas.pagination import PageResult

T = TypeVar("T", bound=BaseRepository)


async def response_one(
    item: dict[str, Any] | None,
    *,
    not_found_message: str = "记录不存在",
) -> ApiResponse[dict]:
    if item is None:
        raise AppException(not_found_message, code=404)
    return success(data=item)


async def response_id(
    record_id: int | None,
    *,
    not_found_message: str = "记录不存在",
) -> ApiResponse[dict]:
    if record_id is None:
        raise AppException(not_found_message, code=404)
    return success(data={"id": record_id})


async def response_list(
    repo: T,
    *,
    page: int,
    page_size: int,
    **filters: Any,
) -> ApiResponse[PageResult[dict]]:
    result = await repo.get_list(page=page, page_size=page_size, **filters)
    return success(data=result)


async def response_updated(
    item: dict[str, Any] | None,
    *,
    not_found_message: str = "记录不存在",
) -> ApiResponse[dict]:
    if item is None:
        raise AppException(not_found_message, code=404)
    return success(data=item, message="更新成功")


async def response_by_field(
    repo: T,
    query: FieldQuery,
    *,
    not_found_message: str = "记录不存在",
) -> ApiResponse[Any]:
    """按 FieldQuery 统一返回 ApiResponse。"""
    result = await repo.query_field(query)

    if query.mode == FieldQueryMode.ONE:
        return await response_one(result, not_found_message=not_found_message)
    if query.mode == FieldQueryMode.ID:
        return await response_id(result, not_found_message=not_found_message)
    if query.mode in (FieldQueryMode.LIST, FieldQueryMode.ALL):
        return success(data=result)

    raise AppException(f"不支持的查询类型: {query.mode}", code=400)
