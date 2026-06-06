"""JWT 签发/解析与密码校验。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.config import Settings

# 密码哈希上下文（bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """将明文密码转为 bcrypt 哈希，写入 users.password_hash。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码是否与库中 password_hash 匹配。"""
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(
    *,
    settings: Settings,
    user_id: int,
    username: str,
) -> tuple[str, str, int]:
    """
    签发 JWT access token。

    返回 (token, jti, expires_in_seconds)。
    jti 会写入 Redis，用于服务端验签与主动失效（登出）。
    """
    jti = uuid4().hex
    expires_in = settings.jwt_access_token_expire_minutes * 60
    expire_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "exp": expire_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_in


def decode_access_token(*, settings: Settings, token: str) -> dict[str, Any]:
    """
    解析 JWT（验签 + 过期检查）。

    仅校验 JWT 本身；是否仍有效还需查 Redis（见 auth/service.py）。
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
