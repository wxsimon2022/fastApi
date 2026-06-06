"""Controller：只负责入参 / 出参，业务逻辑在 services/。"""

from typing import Any

from fastapi import APIRouter

from app.auth.deps import CurrentUser, OptionalUser
from app.schemas.auth import LoginRequest, TokenData
from app.schemas.common import ApiResponse, success
from app.services.deps import AuthServiceDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[TokenData])
async def login(body: LoginRequest, service: AuthServiceDep) -> ApiResponse[TokenData]:
    """登录（不验签）。"""
    token_data = await service.login(body.username, body.password)
    return success(data=TokenData(**token_data), message="登录成功")


@router.post("/logout", response_model=ApiResponse[None])
async def logout(user: CurrentUser, service: AuthServiceDep) -> ApiResponse[None]:
    """登出（必须验签）。"""
    await service.logout(user["jti"])
    return success(data=None, message="已登出")


@router.get("/me", response_model=ApiResponse[dict])
async def get_me(user: CurrentUser, service: AuthServiceDep) -> ApiResponse[dict]:
    """当前登录用户（必须验签）。"""
    return success(data=service.get_profile(user))


@router.get("/demo/public", response_model=ApiResponse[dict])
async def demo_public(service: AuthServiceDep) -> ApiResponse[dict]:
    """示例：不验签 — endpoint 不加 CurrentUser / OptionalUser。"""
    return success(data=service.build_public_demo())


@router.get("/demo/protected", response_model=ApiResponse[dict])
async def demo_protected(
    user: CurrentUser,
    service: AuthServiceDep,
) -> ApiResponse[dict]:
    """示例：必须验签 — 参数声明 user: CurrentUser。"""
    return success(data=service.build_protected_demo(user))


@router.get("/demo/optional", response_model=ApiResponse[dict])
async def demo_optional(
    user: OptionalUser,
    service: AuthServiceDep,
) -> ApiResponse[dict]:
    """示例：可选验签 — 参数声明 user: OptionalUser。"""
    return success(data=service.build_optional_demo(user))
