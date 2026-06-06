"""
接口鉴权依赖（Controller 层使用）。

用法：
    user: CurrentUser   — 必须验签
    user: OptionalUser — 可选验签
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppException
from app.services.deps import AuthServiceDep

_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    service: AuthServiceDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any] | None:
    if credentials is None:
        return None
    return await service.verify_token(credentials.credentials)


async def get_current_user(
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> dict[str, Any]:
    if user is None:
        raise AppException("未登录，请先获取 Token", code=401)
    return user


OptionalUser = Annotated[dict[str, Any] | None, Depends(get_optional_user)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
