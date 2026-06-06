"""Controller：用户接口入参 / 出参。"""

from typing import Any

from fastapi import APIRouter

from app.schemas.common import ApiResponse, success
from app.schemas.pagination import PageResult
from app.schemas.query import ColumnsQuery, FieldParams, PageParams, build_field_query
from app.schemas.user import UserUpdate
from app.services.deps import UserServiceDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=ApiResponse[PageResult[dict]])
async def list_users(
    pagination: PageParams,
    columns: ColumnsQuery,
    service: UserServiceDep,
) -> ApiResponse[PageResult[dict]]:
    """分页查询用户列表。"""
    result = await service.list_paginated(
        page=pagination.page,
        page_size=pagination.page_size,
        columns=columns.columns,
    )
    return success(data=result)


@router.get("/all", response_model=ApiResponse[list])
async def list_all_users(service: UserServiceDep) -> ApiResponse[list]:
    """查询全部用户（固定 id、username）。"""
    items = await service.list_all()
    return success(data=items)


@router.get("/lookup", response_model=ApiResponse[Any])
async def lookup_user(
    lookup: FieldParams,
    pagination: PageParams,
    service: UserServiceDep,
) -> ApiResponse[Any]:
    """按字段查询。"""
    query = build_field_query(lookup, pagination)
    data = await service.lookup(query)
    return success(data=data)


@router.get("/{user_id}", response_model=ApiResponse[dict])
async def get_user(
    user_id: int,
    columns: ColumnsQuery,
    service: UserServiceDep,
) -> ApiResponse[dict]:
    """按 id 查询用户。"""
    user, message = await service.get_by_id(user_id, columns=columns.columns)
    return success(data=user, message=message)


@router.put("/{user_id}", response_model=ApiResponse[dict])
async def update_user(
    user_id: int,
    body: UserUpdate,
    service: UserServiceDep,
) -> ApiResponse[dict]:
    """更新用户。"""
    data = body.model_dump(exclude_unset=True)
    user = await service.update(user_id, data)
    return success(data=user, message="更新成功")
