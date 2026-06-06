from typing import Any

from fastapi import APIRouter

from app.api.helpers import (
    response_all,
    response_by_field,
    response_list,
    response_updated,
)
from app.core.logging import get_logger
from app.config import get_settings
from app.core.exceptions import AppException
from app.db.deps import UserRepo
from app.db.repositories.user import UserRepository
from app.redis.deps import RedisCacheDep
from app.redis.keys import user_cache_key
from app.schemas.common import ApiResponse, success
from app.schemas.user import UserUpdate
from app.schemas.pagination import PageResult
from app.schemas.query import ColumnsQuery, FieldParams, PageParams, build_field_query

router = APIRouter(prefix="/users", tags=["users"])
logger = get_logger(__name__)


@router.get("", response_model=ApiResponse[PageResult[dict]])
async def list_users(
    pagination: PageParams,
    columns: ColumnsQuery,
    repo: UserRepo,
) -> ApiResponse[PageResult[dict]]:
    """分页查询用户列表。可用 fields 指定返回列。"""
    return await response_list(
        repo,
        page=pagination.page,
        page_size=pagination.page_size,
        columns=columns.columns,
    )


@router.get("/all", response_model=ApiResponse[list])
async def list_all_users(repo: UserRepo) -> ApiResponse[list]:
    """查询全部用户列表（不分页），固定返回 id、username。"""
    logger.info("查询全部用户列表（不分页）")
    return await response_all(repo, columns=UserRepository.ALL_LIST_COLUMNS)


@router.get("/lookup", response_model=ApiResponse[Any])
async def lookup_user(
    lookup: FieldParams,
    pagination: PageParams,
    repo: UserRepo,
) -> ApiResponse[Any]:
    """
    按字段查询示例。

    - `type=one`  返回单条记录
    - `type=id`   仅返回 `{"id": 1}`
    - `type=list` 分页返回列表
    """
    query = build_field_query(lookup, pagination)
    return await response_by_field(repo, query, not_found_message="用户不存在")


@router.get("/{user_id}", response_model=ApiResponse[dict])
async def get_user(
    user_id: int,
    columns: ColumnsQuery,
    repo: UserRepo,
    cache: RedisCacheDep,
) -> ApiResponse[dict]:
    """根据用户 id 查询记录。fields 指定返回列时跳过缓存。"""
    if columns.columns is None:
        settings = get_settings()
        key = user_cache_key(user_id)
        cached = await cache.get_json(key)
        if cached is not None:
            return success(data=cached, message="ok(cache)")

        user = await repo.get_one_by_id(user_id)
        if user is None:
            raise AppException("用户不存在", code=404)

        await cache.set_json(key, user, ttl=settings.redis_cache_ttl)
        return success(data=user)

    user = await repo.get_one_by_id(user_id, columns=columns.columns)
    if user is None:
        raise AppException("用户不存在", code=404)
    return success(data=user)


@router.put("/{user_id}", response_model=ApiResponse[dict])
async def update_user(
    user_id: int,
    body: UserUpdate,
    repo: UserRepo,
    cache: RedisCacheDep,
) -> ApiResponse[dict]:
    """更新 o_users 表指定 id 的记录（部分字段）。"""
    data = body.model_dump(exclude_unset=True)
    user = await repo.update_by_id(user_id, data)
    if user is not None:
        await cache.delete(user_cache_key(user_id))
    return await response_updated(user, not_found_message="用户不存在")
