from datetime import date, datetime
from decimal import Decimal
from typing import Any


def serialize_row(row: Any) -> dict[str, Any]:
    """将数据库行转为可 JSON 序列化的 dict。"""
    data = dict(row)
    for key, value in data.items():
        if isinstance(value, (datetime, date)):
            data[key] = value.isoformat()
        elif isinstance(value, Decimal):
            data[key] = float(value)
        elif isinstance(value, bytes):
            data[key] = value.decode("utf-8", errors="replace")
    return data
