from app.db.models.users import Users
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """用户表 o_users。"""

    model = Users

    # 用户列表查询时返回
    ALL_LIST_COLUMNS = ["id", "username","created_at","is_admin"]
