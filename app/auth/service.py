"""JWT + Redis token 生命周期：登录写入、验签读取、登出删除。"""

from __future__ import annotations

from typing import Any

import jwt

from app.config import Settings
from app.core.exceptions import AppException
from app.core.security import create_access_token, decode_access_token
from app.redis.keys import auth_token_key
from app.redis.operations import RedisOps


async def issue_token(
    *,
    settings: Settings,
    cache: RedisOps,
    user_id: int,
    username: str,
) -> dict[str, Any]:
    """
    登录成功后：签发 JWT，并把 jti 写入 Redis。

    Redis 键：auth:token:{jti}
    Redis 值：{"user_id": 1, "username": "admin"}
    TTL 与 JWT 过期时间一致，实现「服务端可控的 token 会话」。
    """
    token, jti, expires_in = create_access_token(
        settings=settings,
        user_id=user_id,
        username=username,
    )
    session = {"user_id": user_id, "username": username}
    await cache.set_json(auth_token_key(jti), session, ttl=expires_in)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


async def verify_token(
    *,
    settings: Settings,
    cache: RedisOps,
    token: str,
) -> dict[str, Any]:
    """
    完整验签流程（接口「必须登录」时使用）：

    1. 解析 JWT（签名、过期）
    2. 用 jti 查 Redis，键不存在视为已登出/失效
    3. 返回当前用户信息 dict
    """
    try:
        payload = decode_access_token(settings=settings, token=token)
    except jwt.PyJWTError as exc:
        raise AppException("Token 无效或已过期", code=401) from exc

    jti = payload.get("jti")
    if not jti:
        raise AppException("Token 缺少 jti", code=401)

    session = await cache.get_json(auth_token_key(jti))
    if session is None:
        raise AppException("Token 已失效，请重新登录", code=401)

    return {
        "user_id": int(session["user_id"]),
        "username": session["username"],
        "jti": jti,
    }


async def revoke_token(*, cache: RedisOps, jti: str) -> None:
    """登出：删除 Redis 中的 token 会话，JWT 即使未过期也无法再通过验签。"""
    await cache.delete(auth_token_key(jti))
