#!/usr/bin/env python3
"""Redis 示例脚本，在项目根目录执行: python scripts/test_redis.py"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.redis.client import redis_client
from app.redis.examples import run_redis_examples
from app.redis.operations import RedisOps


async def main() -> None:
    settings = get_settings()
    await redis_client.startup(settings.redis_url)

    try:
        redis = RedisOps(redis_client.client)
        results = await run_redis_examples(redis)
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    finally:
        await redis_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
