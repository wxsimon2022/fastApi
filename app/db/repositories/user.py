from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """用户表 c_users。"""

    model = User
