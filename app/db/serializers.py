from datetime import date, datetime
from decimal import Decimal
from typing import Any


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def row_to_dict(row: Any) -> dict[str, Any]:
    """将 SQLAlchemy RowMapping 转为可 JSON 序列化的 dict。"""
    data = dict(row)
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.strftime(DATETIME_FORMAT)
        elif isinstance(value, date):
            data[key] = value.isoformat()
        elif isinstance(value, Decimal):
            data[key] = float(value)
        elif isinstance(value, bytes):
            data[key] = value.decode("utf-8", errors="replace")
    return data
