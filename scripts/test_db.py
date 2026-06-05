#!/usr/bin/env python3
"""数据库测试脚本，在项目根目录执行: python scripts/test_db.py"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.db.database import database
from app.db.repositories.user import UserRepository


async def main() -> None:
    settings = get_settings()
    await database.startup(settings.database_url, echo=False)

    try:
        async for session in database.session():
            repo = UserRepository(session, database.users_table)

            user = await repo.get_one_by_id(1)
            page = await repo.get_list(page=1, page_size=10)

            print("get_one_by_id(1):", json.dumps(user, ensure_ascii=False, default=str))
            print(
                "get_list:",
                json.dumps(
                    {
                        "total": page.total,
                        "items": page.items,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )
            break
    finally:
        await database.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
