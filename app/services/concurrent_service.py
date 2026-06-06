"""
并发查库示例 Service。

提供两种并行查库方式：
- thread：ThreadPoolExecutor 多线程 + 同步 Session（本示例重点）
- async：asyncio.gather 并发协程（FastAPI 常规写法，对比用）
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.exceptions import AppException
from app.db.repositories.user import UserRepository
from app.db.sync_database import query_user_by_id_sync

# 全局线程池，避免每次请求重复创建
_THREAD_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="db-query")
MAX_WORKERS = 10
MAX_QUERY_COUNT = 20


class ConcurrentQueryService:
    """多 id 并行查用户示例。"""

    COLUMNS = UserRepository.ALL_LIST_COLUMNS

    async def query_users_threaded(self, user_ids: list[int]) -> dict[str, Any]:
        """
        多线程查库示例。

        每个 user_id 提交到线程池，线程内调用 query_user_by_id_sync，
        各自持有独立 DB 连接，互不干扰。
        """
        self._validate_ids(user_ids)

        loop = asyncio.get_running_loop()
        futures = [
            loop.run_in_executor(
                _THREAD_POOL,
                query_user_by_id_sync,
                user_id,
                self.COLUMNS,
            )
            for user_id in user_ids
        ]
        results = await asyncio.gather(*futures)

        return {
            "mode": "thread_pool",
            "description": "ThreadPoolExecutor + 同步 Session，每线程独立连接",
            "worker_count": min(len(user_ids), MAX_WORKERS),
            "query_count": len(user_ids),
            "items": self._build_items(user_ids, results),
        }

    async def query_users_async(
        self,
        user_ids: list[int],
        repo: UserRepository,
    ) -> dict[str, Any]:
        """
        asyncio 并发查库（对比示例，非多线程）。

        同一请求内共享 AsyncSession，适合 FastAPI 异步栈常规写法。
        """
        self._validate_ids(user_ids)

        tasks = [
            repo.get_one_by_id(user_id, columns=self.COLUMNS)
            for user_id in user_ids
        ]
        results = await asyncio.gather(*tasks)

        return {
            "mode": "asyncio_gather",
            "description": "asyncio.gather 并发协程，共享请求内 AsyncSession",
            "query_count": len(user_ids),
            "items": self._build_items(user_ids, results),
        }

    def _validate_ids(self, user_ids: list[int]) -> None:
        if not user_ids:
            raise AppException("ids 不能为空", code=400)
        if len(user_ids) > MAX_QUERY_COUNT:
            raise AppException(f"单次最多查询 {MAX_QUERY_COUNT} 个 id", code=400)

    def _build_items(
        self,
        user_ids: list[int],
        results: list[dict | None],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for user_id, user in zip(user_ids, results, strict=True):
            items.append(
                {
                    "user_id": user_id,
                    "found": user is not None,
                    "user": user,
                }
            )
        return items
