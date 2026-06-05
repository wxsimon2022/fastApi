from typing import Any, TypeVar

from app.core.exceptions import AppException
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


async def response_one_by(
    repo: T,
    field: str,
    value: Any,
    *,
    not_found_message: str = "记录不存在",
) -> ApiResponse[dict]:
    item = await repo.get_one_by(field, value)
    return await response_one(item, not_found_message=not_found_message)


async def response_id_by(
    repo: T,
    field: str,
    value: Any,
    *,
    not_found_message: str = "记录不存在",
) -> ApiResponse[dict]:
    record_id = await repo.get_id_by(field, value)
    return await response_id(record_id, not_found_message=not_found_message)


async def response_list_by(
    repo: T,
    field: str,
    value: Any,
    *,
    page: int,
    page_size: int,
) -> ApiResponse[PageResult[dict]]:
    result = await repo.get_list_by(
        field,
        value,
        page=page,
        page_size=page_size,
    )
    return success(data=result)


async def response_all_by(
    repo: T,
    field: str,
    value: Any,
    *,
    limit: int = 100,
) -> ApiResponse[list]:
    items = await repo.get_all_by(field, value, limit=limit)
    return success(data=items)


async def response_field_lookup(
    repo: T,
    *,
    field: str,
    value: Any,
    lookup_type: str,
    page: int = 1,
    page_size: int = 10,
    not_found_message: str = "记录不存在",
) -> ApiResponse[Any]:
    """按字段统一查询：one / list / id。"""
    if lookup_type == "one":
        return await response_one_by(repo, field, value, not_found_message=not_found_message)
    if lookup_type == "id":
        return await response_id_by(repo, field, value, not_found_message=not_found_message)
    if lookup_type == "list":
        return await response_list_by(
            repo,
            field,
            value,
            page=page,
            page_size=page_size,
        )
    raise AppException(f"不支持的查询类型: {lookup_type}", code=400)
