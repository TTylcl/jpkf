""" dal/query/__init__.py """
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageResult:
    """统一分页返回模型"""
    items: list[Any] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    def __str__(self) -> str:
        """返回 LLM 友好的 JSON，ORM 对象自动转 dict"""
        import json

        def _serialize(item):
            if hasattr(item, "to_dict"):
                return item.to_dict()
            if hasattr(item, "__dict__"):
                return {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
            return str(item)

        return json.dumps({
            "items": [_serialize(it) for it in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }, ensure_ascii=False, indent=2)
    
from dal.query.student_course_query_service import StudentCourseQueryService, StudentCourseFilters