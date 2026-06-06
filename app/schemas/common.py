from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_serializer

T = TypeVar("T")

# 业务成功状态码（与 HTTP 200 保持一致）
SUCCESS_CODE = 200


def api_body(code: int, data: Any = None, message: str = "ok") -> dict[str, Any]:
    """构造固定字段顺序的响应体：code → data → message"""
    return {"code": code, "data": data, "message": message}


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(SUCCESS_CODE, description="业务状态码，200 表示成功")
    data: T | None = Field(None, description="业务数据")
    message: str = Field("ok", description="提示信息")

    @model_serializer(mode="plain")
    def _serialize_ordered(self) -> dict[str, Any]:
        return api_body(self.code, self.data, self.message)


def success(
    data: T | None = None,
    message: str = "ok",
    code: int = SUCCESS_CODE,
) -> ApiResponse[T]:
    return ApiResponse(code=code, data=data, message=message)


def fail(
    message: str,
    code: int = 400,
    data: Any = None,
) -> ApiResponse[Any]:
    return ApiResponse(code=code, data=data, message=message)
