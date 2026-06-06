"""生成 bcrypt 密码哈希，用于初始化 users.password_hash。"""

import sys

from app.core.security import hash_password


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python scripts/hash_password.py <明文密码>")
        sys.exit(1)
    print(hash_password(sys.argv[1]))


if __name__ == "__main__":
    main()
