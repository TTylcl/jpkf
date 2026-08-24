"""
service/parent_student_service.py
家长-学生关联 Service —— 直接用 DAO，不需要 QueryService
"""

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao
from core.service.models import ServiceResult
from dal.dao.parent_student_dao import ParentStudentDao
from schemas.parent_student_schema import ParentStudentListResponse, ParentStudentResponse, UnbindParentStudentResponse

from dal.query.student_course_query_service import StudentCourseQueryService, StudentCourseFilters
from dal.query.schedule_query_service import ScheduleQueryService, ScheduleFilters
from schemas.student_course_schema import StudentCourseResponse, StudentCourseListResponse
from schemas.schedule_schemas import ScheduleItem, ScheduleResult
from dal.models.enums import StudentCourseStatus




class ParentStudentService:
    resource = "parent_student" 
    dao_class = ParentStudentDao

    @tool(ToolMeta(
        name="get_my_children",
        description="查询家长绑定的所有学生",
        parameters={"parent_id": {"type": "integer"}},
        require_permission=True,
        owner_param="parent_id",
        owner_roles=("parent",),
    ))
    async def get_my_children(self, ctx: CTX, parent_id: int) -> ParentStudentListResponse | ServiceResult:
        dao: ParentStudentDao = get_dao(ctx, self.dao_class)
        students = await dao.get_parent_students(parent_id)
        return ParentStudentListResponse(items=students, total=len(students))

    @tool(ToolMeta(
        name="get_student_parents",
        description="查询学生的所有家长",
        parameters={"student_id": {"type": "integer"}},
        require_permission=True,
    ))
    async def get_student_parents(self, ctx: CTX, student_id: int) -> ParentStudentListResponse | ServiceResult:
        dao: ParentStudentDao = get_dao(ctx, self.dao_class)
        parents = await dao.get_student_parents(student_id)
        return ParentStudentListResponse(items=parents, total=len(parents))

    @tool(ToolMeta(
        name="bind_parent_student",
        description="绑定家长和学生",
        parameters={
            "parent_id":  {"type": "integer"},
            "student_id": {"type": "integer"},
            "relation":   {"type": "string", "description": "关系：father / mother / guardian"},
        },
        require_permission=True,
    ))
    async def bind_parent_student(
        self, ctx: CTX, parent_id: int, student_id: int, relation: str = "guardian"
    ) -> ParentStudentResponse | ServiceResult:
        dao: ParentStudentDao = get_dao(ctx, self.dao_class)
        record = await dao.bind(parent_id, student_id, relation)
        return ParentStudentResponse.from_orm_model(record)

    @tool(ToolMeta(
        name="unbind_parent_student",
        description="解绑家长和学生",
        parameters={"parent_id": {"type": "integer"}, "student_id": {"type": "integer"}},
        require_permission=True,
    ))
    async def unbind_parent_student(
        self, ctx: CTX, parent_id: int, student_id: int
    )  -> UnbindParentStudentResponse | ServiceResult:
        dao: ParentStudentDao = get_dao(ctx, self.dao_class)
        success = await dao.unbind(parent_id, student_id)
        if not success:
            return ServiceResult.error(message="解绑失败，可能关系不存在", code=400, trace_id=ctx.trace_id)
        return UnbindParentStudentResponse(message="解绑成功")
    
    #=========家长查课======================
    @tool(ToolMeta(
        name="get_child_courses",
        description="家长查看指定孩子的选课列表。",
        parameters={
            "parent_id": {"type": "integer", "description": "家长用户ID"},
            "child_id": {"type": "integer", "description": "孩子（学生）ID"},
            "page": {"type": "integer", "default": 1},           # ← 换成分页
            "page_size": {"type": "integer", "default": 20},
        },
        require_permission=True,
        owner_param="parent_id",
        owner_roles=("parent",),
    ))
    async def get_child_courses(
        self,
        ctx: CTX,
        parent_id: int,
        child_id: int,
        page: int = 1,
        page_size: int = 20,
    ) ->ServiceResult:
        """家长查看指定孩子的选课"""
        # ① 验证绑定关系
        dao: ParentStudentDao = get_dao(ctx, self.dao_class)
        bindings = await dao.get_parent_students(parent_id)
        if not any(b.student_id == child_id for b in bindings):
            return ServiceResult.error(
                message=f"家长与孩子无绑定关系（家长ID:{parent_id}，孩子ID:{child_id}）",
                code=403,
                trace_id=ctx.trace_id,
            )

        # ② 查选课
        

        qs = StudentCourseQueryService(ctx.session) # 选课查询服务
        result = await qs.query_student_courses(
            filters=StudentCourseFilters(
                student_id=child_id,
                status=StudentCourseStatus.ACTIVE,
            ),
            page=page, page_size=page_size,
        )
        items = [StudentCourseResponse.from_orm_model(item) for item in result.items]
      
        return ServiceResult.ok(
            data=StudentCourseListResponse(items=items, total=result.total),
            trace_id=ctx.trace_id,
        )
    
    @tool(ToolMeta(
        name="get_child_schedules",
        description="家长查看指定孩子的排课。不传day_of_week则查整周所有排课。",
        parameters={
            "parent_id": {"type": "integer", "description": "家长用户ID"},
            "child_id": {"type": "integer", "description": "孩子（学生）ID"},
            "day_of_week": {"type": "integer", "description": "星期几：1=周一...7=周日，不传=查整周", "default": None},
        },
        require_permission=True,
        owner_param="parent_id",
        owner_roles=("parent",),
    ))
    async def get_child_schedules(
        self,
        ctx: CTX,
        parent_id: int,
        child_id: int,
        day_of_week: int | None = None,
    ) ->ServiceResult:
        """家长查看指定孩子的排课"""
        # ① 验证绑定关系
        dao: ParentStudentDao = get_dao(ctx, self.dao_class)
        bindings = await dao.get_parent_students(parent_id)
        if not any(b.student_id == child_id for b in bindings):
            return ServiceResult.error(
                message=f'家长{parent_id}与学生{child_id}无绑定关系',
                code=403,
                trace_id=ctx.trace_id,
            )
        qs = ScheduleQueryService(ctx.session)  # 排课查询服务
        # day_of_week=None → 查整周；指定具体值 → 只查那一天
        result = await qs.query_schedules(
            filters=ScheduleFilters(
                student_id=child_id,
                day_of_week=day_of_week,
            ),
        )

        
        # 返回结果
        return ServiceResult.ok(
            data=ScheduleResult(items=result.items),
            trace_id=ctx.trace_id,
        )

        









