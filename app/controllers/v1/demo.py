"""Controller：并发查库示例（多线程 / asyncio 对比）。"""

from typing import Literal

from fastapi import APIRouter, Query

from app.core.exceptions import AppException
from app.db.deps import UserRepo
from app.schemas.common import ApiResponse, success
from app.services.deps import ConcurrentQueryServiceDep

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/concurrent-users", response_model=ApiResponse[dict])
async def concurrent_query_users(
    service: ConcurrentQueryServiceDep,
    repo: UserRepo,
    ids: str = Query(..., description="用户 id 列表，逗号分隔，如 1,2,3"),
    mode: Literal["thread", "async"] = Query(
        "thread",
        description="thread=多线程+同步Session；async=asyncio并发（对比）",
    ),
) -> ApiResponse[dict]:
    """
    并行按 id 查用户示例。

    - ``mode=thread``：ThreadPoolExecutor 多线程，每线程独立同步 DB 连接
    - ``mode=async``：asyncio.gather 并发协程（FastAPI 常规写法）
    """
    user_ids = _parse_ids(ids)

    if mode == "thread":
        data = await service.query_users_threaded(user_ids)
    else:
        data = await service.query_users_async(user_ids, repo)

    return success(data=data)


def _parse_ids(raw: str) -> list[int]:
    """解析 ids=1,2,3 为整数列表。"""
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        raise AppException("ids 不能为空", code=400)

    user_ids: list[int] = []
    for part in parts:
        if not part.isdigit():
            raise AppException(f"无效的 id: {part}", code=400)
        user_ids.append(int(part))
    return user_ids
