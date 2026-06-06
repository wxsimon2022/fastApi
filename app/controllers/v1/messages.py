"""Controller：c_messages 接口入参 / 出参。"""

from typing import Any

from fastapi import APIRouter

from app.schemas.common import ApiResponse, success
from app.schemas.messages import MessagesUpdate
from app.schemas.pagination import PageResult
from app.schemas.query import ColumnsQuery, FieldParams, PageParams, build_field_query
from app.services.deps import MessageServiceDep

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=ApiResponse[PageResult[dict]])
async def list_messages(
    pagination: PageParams,
    columns: ColumnsQuery,
    service: MessageServiceDep,
) -> ApiResponse[PageResult[dict]]:
    result = await service.list_paginated(
        page=pagination.page,
        page_size=pagination.page_size,
        columns=columns.columns,
    )
    return success(data=result)


@router.get("/all", response_model=ApiResponse[list])
async def list_all_messages(service: MessageServiceDep) -> ApiResponse[list]:
    items = await service.list_all()
    return success(data=items)


@router.get("/lookup", response_model=ApiResponse[Any])
async def lookup_message(
    lookup: FieldParams,
    pagination: PageParams,
    service: MessageServiceDep,
) -> ApiResponse[Any]:
    query = build_field_query(lookup, pagination)
    data = await service.lookup(query)
    return success(data=data)


@router.get("/{message_id}", response_model=ApiResponse[dict])
async def get_message(
    message_id: int,
    columns: ColumnsQuery,
    service: MessageServiceDep,
) -> ApiResponse[dict]:
    item = await service.get_by_id(message_id, columns=columns.columns)
    return success(data=item)


@router.put("/{message_id}", response_model=ApiResponse[dict])
async def update_message(
    message_id: int,
    body: MessagesUpdate,
    service: MessageServiceDep,
) -> ApiResponse[dict]:
    data = body.model_dump(exclude_unset=True)
    item = await service.update(message_id, data)
    return success(data=item, message="更新成功")
