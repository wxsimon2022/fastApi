from app.db.models.users import Users
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """用户表 o_users。"""

    model = Users
