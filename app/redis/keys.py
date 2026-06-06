USER_KEY_PREFIX = "user:"


def user_cache_key(user_id: int) -> str:
    return f"{USER_KEY_PREFIX}{user_id}"
