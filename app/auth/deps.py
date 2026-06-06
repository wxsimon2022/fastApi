"""
接口鉴权依赖。

用法（在 endpoint 参数上声明即可）：

    # 必须登录，无 token 或 token 无效 → 401
    async def protected_api(user: CurrentUser): ...

    # 可选登录，无 token → user 为 None；带了 token 则必须有效
    async def optional_api(user: OptionalUser): ...

    # 完全公开，不加任何鉴权依赖
    async def public_api(): ...
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import verify_token
from app.config import get_settings
from app.core.exceptions import AppException
from app.redis.deps import RedisCacheDep

# auto_error=False：无 Authorization 头时不抛 403，便于「可选验签」
_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    cache: RedisCacheDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any] | None:
    """
    可选验签依赖。

    - 未传 token：返回 None（匿名访问）
    - 传了 token：走完整验签，失败抛 401
    """
    if credentials is None:
        return None

    settings = get_settings()
    return await verify_token(
        settings=settings,
        cache=cache,
        token=credentials.credentials,
    )


async def get_current_user(
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """
    必须验签依赖。

    - 未传 token → 401
    - token 无效/Redis 中已失效 → 401
    """
    if user is None:
        raise AppException("未登录，请先获取 Token", code=401)
    return user


# 类型别名，接口里直接写参数类型即可
OptionalUser = Annotated[dict[str, Any] | None, Depends(get_optional_user)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
