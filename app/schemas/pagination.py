from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T] = Field(description="当前页数据")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码，从 1 开始")
    page_size: int = Field(description="每页条数")
    pages: int = Field(description="总页数")
