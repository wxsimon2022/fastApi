from typing import Any

from fastapi import APIRouter

from app.api.helpers import response_by_field, response_list, response_one
from app.db.deps import UserRepo
from app.schemas.common import ApiResponse
from app.schemas.pagination import PageResult
from app.schemas.query import FieldParams, PageParams, build_field_query

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=ApiResponse[PageResult[dict]])
async def list_users(
    pagination: PageParams,
    repo: UserRepo,
) -> ApiResponse[PageResult[dict]]:
    """分页查询用户列表。"""
    return await response_list(
        repo,
        page=pagination.page,
        page_size=pagination.page_size,
    )


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
async def get_user(user_id: int, repo: UserRepo) -> ApiResponse[dict]:
    """根据用户 id 查询记录。"""
    user = await repo.get_one_by_id(user_id)
    return await response_one(user, not_found_message="用户不存在")
