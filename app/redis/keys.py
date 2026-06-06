USER_KEY_PREFIX = "user:"
AUTH_TOKEN_KEY_PREFIX = "auth:token:"


def user_cache_key(user_id: int) -> str:
    return f"{USER_KEY_PREFIX}{user_id}"


def auth_token_key(jti: str) -> str:
    """JWT 会话在 Redis 中的键，值为 user_id/username，TTL 与 token 过期一致。"""
    return f"{AUTH_TOKEN_KEY_PREFIX}{jti}"
