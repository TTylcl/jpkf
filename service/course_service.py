"""
service/course_service.py
课程 Service —— AI Agent 工具层
"""
from __future__ import annotations

from datetime import datetime

from core.context import CTX
from core.service.models import ServiceResult
from core.service.utils import get_dao
from core.service.decorators import tool, ToolMeta
from dal.dao.course_dao import CourseDao
from dal.query.course_query_service import CourseQueryService, CourseFilters
from dal.query import PageResult
from dal.models.enums import CourseType, CourseStatus


class CourseService:
    resource = "course" 
    dao_class = CourseDao

    # ==================== 查询 ====================

    @tool(ToolMeta(
        name="query_courses",
        description="灵活查询课程列表。支持关键词、教师、类型、状态、时间范围等组合过滤，支持分页和排序。",
        parameters={
            "keyword":        {"type": "string",  "description": "模糊搜索：课程名 / 编码 / 教师名", "default": None},
            "teacher_id":     {"type": "integer", "description": "教师 ID", "default": None},
            "course_type":    {"type": "string",  "description": "课程类型", "default": None},
            "status":         {"type": "string",  "description": "课程状态", "default": None},
            "created_after":  {"type": "string",  "description": "创建时间起始（ISO 格式）", "default": None},
            "created_before": {"type": "string",  "description": "创建时间截止（ISO 格式）", "default": None},
            "page":           {"type": "integer", "default": 1},
            "page_size":      {"type": "integer", "default": 20},
            "order_by":       {"type": "string",  "description": "排序字段，- 前缀表示降序", "default": None},
        },
        require_permission=True,
    ))
    async def query_courses(
        self,
        ctx: CTX,
        keyword: str | None = None,
        teacher_id: int | None = None,
        course_type: str | None = None,
        status: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str | None = None,
    ) -> ServiceResult:
        qs = CourseQueryService(ctx.session)

        filters = CourseFilters(
            keyword=keyword,
            teacher_id=teacher_id,
            course_type=CourseType(course_type) if course_type else None,
            status=CourseStatus(int(status)) if status else None,
            created_after=datetime.fromisoformat(created_after) if created_after else None,
            created_before=datetime.fromisoformat(created_before) if created_before else None,
        )

        result: PageResult = await qs.query_courses(filters, page=page, page_size=page_size, order_by=order_by)
        return ServiceResult.ok(data=result, trace_id=ctx.trace_id)

    @tool(ToolMeta(
        name="get_course",
        description="根据课程 ID 获取课程详情（含价格、课时、教师、描述等完整信息）",
        parameters={"course_id": {"type": "integer", "description": "课程 ID"}},
        require_permission=True,
    ))
    async def get_course(self, ctx: CTX, course_id: int) -> ServiceResult:
        dao: CourseDao = get_dao(ctx, self.dao_class)
        course = await dao.get_by_id(course_id)
        if not course:
            return ServiceResult.error(message=f"课程#{course_id}不存在", code=404, trace_id=ctx.trace_id)
        return ServiceResult.ok(data=course.to_dict(), trace_id=ctx.trace_id)

    @tool(ToolMeta(
        name="get_course_by_code",
        description="根据课程编码查询课程",
        parameters={"course_code": {"type": "string", "description": "课程编码"}},
        require_permission=True,
    ))
    async def get_course_by_code(self, ctx: CTX, course_code: str) -> ServiceResult:
        dao: CourseDao = get_dao(ctx, self.dao_class)
        course = await dao.get_by_course_code(course_code)
        if not course:
            return ServiceResult.error(message=f"课程编码「{course_code}」对应课程不存在", code=404, trace_id=ctx.trace_id)
        return ServiceResult.ok(data=course.to_dict(), trace_id=ctx.trace_id)

    # ==================== 写入 ====================

    @tool(ToolMeta(
        name="create_course",
        description="创建新课程。⚠️ 调用前必须已向用户确认全部六项信息（名称、教师、类型、价格、课时、描述），且用户已明确同意创建。禁止在信息不全时调用。course_type 可选值：REGULAR(正课) / TRIAL(体验课) / SUMMER(暑假课)",
        parameters={
            "course_name":    {"type": "string",  "description": "课程名称"},
            "teacher_id":     {"type": "integer", "description": "教师 ID"},
            "course_type":    {"type": "string",  "description": "课程类型：REGULAR / TRIAL / SUMMER"},
            "price":          {"type": "number",  "description": "课程单价（元）", "default": 0},
            "total_lessons":  {"type": "integer", "description": "总课时数", "default": 0},
            "course_code":    {"type": "string",  "description": "课程编码（可选，不填则自动生成）", "default": ""},
            "description":    {"type": "string",  "description": "课程描述（可选）", "default": ""},
        },
        require_permission=True,
    ))
    async def create_course(
        self, ctx: CTX, course_name: str,
        teacher_id: int, course_type: str,
        price: float = 0.0,
        total_lessons: int = 0,
        course_code: str = "",
        description: str = "",
    ) -> ServiceResult:
        dao: CourseDao = get_dao(ctx, self.dao_class)

        if not course_code:
            import uuid
            course_code = f"C{uuid.uuid4().hex[:8].upper()}"

        if await dao.exists_by_course_code(course_code):
            return ServiceResult.error(message=f"课程编码已存在: {course_code}", code=409, trace_id=ctx.trace_id)

        course = await dao.create(
            course_name=course_name,
            course_code=course_code,
            teacher_id=teacher_id,
            course_type=CourseType(course_type).value,
            price=price,
            total_lessons=total_lessons,
            description=description,
        )
        return ServiceResult.ok(data=course, trace_id=ctx.trace_id, message="课程创建成功")

    # ==================== 修改 ====================
    #可以修改课程名称、教师、课程类型、单价、总课时数、课程描述
    @tool(ToolMeta(
        name="update_course",
        description="修改课程信息。course_type 可选值：REGULAR(正课) / TRIAL(体验课) / SUMMER(暑假课)",
        parameters={
            "course_id":      {"type": "integer", "description": "课程 ID"},
            "course_name":    {"type": "string",  "description": "课程名称", "default": None},
            "teacher_id":     {"type": "integer", "description": "教师 ID", "default": None},
            "course_type":    {"type": "string",  "description": "课程类型：REGULAR / TRIAL / SUMMER", "default": None},
            "price":          {"type": "number",  "description": "课程单价（元）", "default": None},
            "total_lessons":  {"type": "integer", "description": "总课时数", "default": None},
            "description":    {"type": "string",  "description": "课程描述", "default": None},
        },
        require_permission=True, # 写权限
    ))
    async def update_course(
        self, ctx: CTX, course_id: int,
        course_name: str = None, teacher_id: int = None,
        course_type: str = None, price: float = None,
        total_lessons: int = None, description: str = None,
    ) -> ServiceResult:
        dao: CourseDao = get_dao(ctx, self.dao_class)
        existing = await dao.get_by_id(course_id)
        if not existing:
            return ServiceResult.error(message=f"课程#{course_id}不存在", code=404, trace_id=ctx.trace_id)

        updates = {k:v for k ,v in{
            "course_name": course_name,
            "teacher_id": teacher_id,
            "course_type": course_type,
            "price": price,
            "total_lessons": total_lessons,
            "description": description,
        }.items() if v is not None}
        if not updates:
            return ServiceResult.error(message="没有提供任何更新字段", code=400, trace_id=ctx.trace_id)
        updated = await dao.update(course_id, **updates)
        return ServiceResult.ok(data=updated, trace_id=ctx.trace_id, message="课程信息已更新")




    @tool(ToolMeta(
        name="delete_course",
        description="软删除课程",
        parameters={"course_id": {"type": "integer", "description": "课程 ID"}},
        require_permission=True,
    ))
    async def delete_course(self, ctx: CTX, course_id: int) -> ServiceResult:
        dao: CourseDao = get_dao(ctx, self.dao_class)
        existing = await dao.get_by_id(course_id)
        if not existing:
            return ServiceResult.error(message=f"课程#{course_id}不存在", code=404, trace_id=ctx.trace_id)
        await dao.soft_delete(course_id)
        return ServiceResult.ok(data=None, trace_id=ctx.trace_id, message=f"课程#{course_id}已删除")