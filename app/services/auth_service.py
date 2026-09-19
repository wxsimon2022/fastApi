"""JWT 登录、验签、登出等业务逻辑。"""

from __future__ import annotations

import random
from typing import Any

import jwt

from app.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.db.repositories.user import UserRepository
from app.redis.keys import auth_token_key
from app.redis.operations import RedisOps
from datetime import datetime

logger = get_logger(__name__)


class AuthService:
    """认证相关业务：登录、Token 验签、登出、示例数据组装。"""

    def __init__(
            self,
            *,
            repo: UserRepository,
            cache: RedisOps,
            settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._cache = cache
        self._settings = settings or get_settings()

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """校验账号密码，签发 JWT 并写入 Redis。"""
        user = await self._repo.get_one_by("username", username)
        if user is None or not verify_password(password, user["password_hash"]):
            raise AppException("用户名或密码错误", code=401)

        return await self._issue_token(
            user_id=int(user["id"]),
            username=user["username"],
        )

    async def logout(self, jti: str) -> None:
        """登出：删除 Redis 中的 token 会话。"""
        await self._cache.delete(auth_token_key(jti))

    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        完整验签：JWT 签名/过期 + Redis 会话是否存在。
        供 CurrentUser / OptionalUser 依赖调用。
        """
        try:
            payload = decode_access_token(settings=self._settings, token=token)
        except jwt.PyJWTError as exc:
            logger.error("Token 无效或已过期", exc_info=exc)
            raise AppException("Token 无效或已过期", code=401) from exc

        jti = payload.get("jti")
        if not jti:
            raise AppException("Token 缺少 jti", code=401)

        session = await self._cache.get_json(auth_token_key(jti))
        if session is None:
            raise AppException("Token 已失效，请重新登录", code=401)

        return {
            "user_id": int(session["user_id"]),
            "username": session["username"],
            "jti": jti,
        }

    def get_profile(self, user: dict[str, Any]) -> dict[str, Any]:
        """当前登录用户基本信息。"""
        return {
            "user_id": user["user_id"],
            "username": user["username"],
        }

    def build_public_demo(self) -> dict[str, Any]:
        return {"mode": "public", "message": "无需 Token 即可访问"}

    def build_protected_demo(self, user: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": "protected",
            "message": "已通过 JWT + Redis 验签",
            "user_id": user["user_id"],
            "username": user["username"],
        }

    def build_optional_demo(self, user: dict[str, Any] | None) -> dict[str, Any]:
        if user is None:
            return {
                "mode": "optional",
                "logged_in": False,
                "message": "未登录，匿名访问",
            }
        return {
            "mode": "optional",
            "logged_in": True,
            "message": "已登录，返回用户信息",
            "user_id": user["user_id"],
            "username": user["username"],
        }

    async def _issue_token(self, *, user_id: int, username: str) -> dict[str, Any]:
        token, jti, expires_in = create_access_token(
            settings=self._settings,
            user_id=user_id,
            username=username,
        )
        session = {"user_id": user_id, "username": username}
        await self._cache.set_json(
            auth_token_key(jti),
            session,
            ttl=expires_in,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    async def build_test_demo(self) -> dict[str, Any]:
        users = await self._repo.get_all(
            columns=UserRepository.ALL_LIST_COLUMNS,
        )

        user = users[0]
        logger.warn("变更前:user: %s", user)
        is_admin = random.randrange(0, 100)
        update_data = {"is_admin": is_admin, "username": "wx" + str(is_admin)}

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self._repo.update_by_id(user["id"], update_data)

        logger.warn("变更后:user: %s", user)

        await self._cache.incr("test_key_incr", 1)
        test_value = await self._cache.get("test_key_incr")
        return {
            "mode": "test",
            "message": "已登录，返回用户信息",
            "user_list": users,
            "is_admin": is_admin,
            "test_value": test_value,
            "now": now,
        }
