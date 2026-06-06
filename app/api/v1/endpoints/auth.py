"""
JWT 鉴权示例接口。

流程简述
--------
1. POST /auth/login  登录，返回 access_token（同时写入 Redis）
2. 请求需登录的接口时，Header 带上：Authorization: Bearer <access_token>
3. POST /auth/logout 登出，删除 Redis 中的 token，旧 token 立即失效

接口验签方式
------------
- 不验签：endpoint 不加 CurrentUser / OptionalUser 依赖（如 /auth/demo/public）
- 必须验签：参数声明 user: CurrentUser
- 可选验签：参数声明 user: OptionalUser（未登录可访问，登录后返回更多信息）
"""

from typing import Any

from fastapi import APIRouter

from app.auth.deps import CurrentUser, OptionalUser
from app.auth.service import issue_token, revoke_token
from app.config import get_settings
from app.core.exceptions import AppException
from app.core.security import verify_password
from app.db.deps import UserRepo
from app.redis.deps import RedisCacheDep
from app.schemas.auth import LoginRequest, TokenData
from app.schemas.common import ApiResponse, success

router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------------------------------------------ #
# 登录 / 登出 / 当前用户
# ------------------------------------------------------------------ #


@router.post("/login", response_model=ApiResponse[TokenData])
async def login(
    body: LoginRequest,
    repo: UserRepo,
    cache: RedisCacheDep,
) -> ApiResponse[TokenData]:
    """
    登录（不验签）。

    校验用户名密码后签发 JWT，并把 jti 存入 Redis。
    users.password_hash 需为 bcrypt 哈希（见 scripts/hash_password.py）。
    """
    settings = get_settings()
    user = await repo.get_one_by("username", body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise AppException("用户名或密码错误", code=401)

    token_data = await issue_token(
        settings=settings,
        cache=cache,
        user_id=int(user["id"]),
        username=user["username"],
    )
    return success(data=TokenData(**token_data), message="登录成功")


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    user: CurrentUser,
    cache: RedisCacheDep,
) -> ApiResponse[None]:
    """登出（必须验签）。删除 Redis 中的 token 会话。"""
    await revoke_token(cache=cache, jti=user["jti"])
    return success(data=None, message="已登出")


@router.get("/me", response_model=ApiResponse[dict])
async def get_me(user: CurrentUser) -> ApiResponse[dict]:
    """获取当前登录用户（必须验签）。"""
    return success(
        data={
            "user_id": user["user_id"],
            "username": user["username"],
        }
    )


# ------------------------------------------------------------------ #
# 三种验签模式示例（注释对照接口写法）
# ------------------------------------------------------------------ #


@router.get("/demo/public", response_model=ApiResponse[dict])
async def demo_public() -> ApiResponse[dict]:
    """
    示例：完全不验签。

    不需要 Authorization 头，任何人可访问。
    """
    return success(
        data={"mode": "public", "message": "无需 Token 即可访问"},
    )


@router.get("/demo/protected", response_model=ApiResponse[dict])
async def demo_protected(user: CurrentUser) -> ApiResponse[dict]:
    """
    示例：必须验签。

    参数加上 ``user: CurrentUser`` 即可：
    - 无 Token → 401
    - Token 无效或 Redis 中已删除 → 401
    """
    return success(
        data={
            "mode": "protected",
            "message": "已通过 JWT + Redis 验签",
            "user_id": user["user_id"],
            "username": user["username"],
        }
    )


@router.get("/demo/optional", response_model=ApiResponse[dict])
async def demo_optional(user: OptionalUser) -> ApiResponse[dict]:
    """
    示例：可选验签。

    参数使用 ``user: OptionalUser``：
    - 无 Token → user 为 None，按匿名逻辑返回
    - 有 Token → 必须有效，否则 401
    """
    if user is None:
        return success(
            data={
                "mode": "optional",
                "logged_in": False,
                "message": "未登录，匿名访问",
            }
        )

    return success(
        data={
            "mode": "optional",
            "logged_in": True,
            "message": "已登录，返回用户信息",
            "user_id": user["user_id"],
            "username": user["username"],
        }
    )
