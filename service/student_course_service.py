"""
service/student_course_service.py
学生选课 Service —— 直接用 DAO，不需要 QueryService
"""

from core.context import CTX
from core.service.decorators import tool, ToolMeta
from core.service.utils import get_dao
from core.service.models import ServiceResult
from dal.dao.student_course_dao import StudentCourseDao
from dal.dao.course_dao import CourseDao
from schemas.student_course_schema import EnrollResponse, EnrollmentCheckResponse, StudentCourseResponse, StudentCourseListResponse


class StudentCourseService:
    resource = "student_course"
    dao_class = StudentCourseDao

    @tool(ToolMeta(
        name="get_my_courses",
        description="查询学生的所有选课记录（含课程名称、价格、课时、教师等完整信息）",
        parameters={"student_id": {"type": "integer"}},
        require_permission=True,
    ))
    async def get_my_courses(self, ctx: CTX, student_id: int) -> ServiceResult:
        """学生查看自己的选课，返回与 get_child_courses 一致的结构化数据"""
        from dal.query.student_course_query_service import StudentCourseQueryService, StudentCourseFilters
        from dal.models.enums import StudentCourseStatus as Scs

        qs = StudentCourseQueryService(ctx.session)
        result = await qs.query_student_courses(
            filters=StudentCourseFilters(
                student_id=student_id,
                status=Scs.ACTIVE,
            ),
            page=1, page_size=50,
        )
        items = [StudentCourseResponse.from_orm_model(item) for item in result.items]
        return ServiceResult.ok(
            data=StudentCourseListResponse(items=items, total=result.total),
            trace_id=ctx.trace_id,
        )

    @tool(ToolMeta(
        name="get_course_students",
        description="查询某门课的所有在读学生",
        parameters={"course_id": {"type": "integer"}},
        require_permission=True,
    ))
    async def get_course_students(self, ctx: CTX, course_id: int) -> ServiceResult:
        dao: StudentCourseDao = get_dao(ctx, self.dao_class)
        students = await dao.list_course_students(course_id)
        return ServiceResult.ok(data=students, trace_id=ctx.trace_id)

    @tool(ToolMeta(
        name="check_enrollment",
        description="检查学生是否已选某门课",
        parameters={"student_id": {"type": "integer","description": "学生ID"}, "course_id": {"type": "integer","description": "课程ID"}},
        require_permission=True,
    ))
    async def check_enrollment(self, ctx: CTX, student_id: int, course_id: int) -> EnrollmentCheckResponse | ServiceResult:
        dao: StudentCourseDao = get_dao(ctx, self.dao_class)
        record = await dao.get_by_student_and_course(student_id, course_id)
        return EnrollmentCheckResponse(enrolled=bool(record))

    @tool(ToolMeta(
        name="enroll_student",
        description="学生报名课程。报名时自动从课程复制 total_lessons 到学生的 purchased_lessons 和 remaining_lessons。",
        parameters={"student_id": {"type": "integer"}, "course_id": {"type": "integer"}},
        require_permission=True,
    ))
    async def enroll_student(self, ctx: CTX, student_id: int, course_id: int) -> EnrollResponse | ServiceResult:
        dao: StudentCourseDao = get_dao(ctx, self.dao_class)

        # 校验课程是否存在
        course_dao = CourseDao(ctx.session)
        course = await course_dao.get_by_id(course_id)
        if not course:
            return ServiceResult.error(
                message=f"课程#{course_id}不存在", code=404, trace_id=ctx.trace_id
            )

        existing = await dao.get_by_student_and_course(student_id, course_id)
        if existing:
            if existing.status == "active":
                return ServiceResult.error(
                    message="学生已报名该课程", code=409,
                    data=EnrollResponse(
                        id=existing.id, student_id=existing.student_id,
                        student_name=existing.student.real_name if existing.student else "",
                        course_id=existing.course_id,
                        course_name=existing.course.course_name if existing.course else "",
                        status=existing.status,
                        enrolled_at=existing.enrolled_at.isoformat() if existing.enrolled_at else None,
                        message="学生已报名该课程",
                    ),
                    trace_id=ctx.trace_id,
                )
            elif existing.status == "dropped":
                # 重新激活时也更新课时数据
                total = course.total_lessons or 0
                await dao.update(existing.id, status="active",
                                 purchased_lessons=total, remaining_lessons=total)
                return EnrollResponse(
                    id=existing.id, student_id=existing.student_id,
                    student_name=existing.student.real_name if existing.student else "",
                    course_id=existing.course_id,
                    course_name=existing.course.course_name if existing.course else "",
                    status=existing.status,
                    enrolled_at=existing.enrolled_at.isoformat() if existing.enrolled_at else None,
                    message=f"报名已重新激活，课时已重置为 {total} 节",
                )

        # 新报名：从课程复制总课时到 purchased_lessons 和 remaining_lessons
        total_lessons = course.total_lessons or 0
        new_record = await dao.create(
            student_id=student_id,
            course_id=course_id,
            status="active",
            purchased_lessons=total_lessons,
            remaining_lessons=total_lessons,
        )
        return EnrollResponse(
            id=new_record.id,
            student_id=new_record.student_id,
            student_name=new_record.student.real_name if new_record.student else "",
            course_id=new_record.course_id,
            course_name=new_record.course.course_name if new_record.course else "",
            status=new_record.status,
            enrolled_at=new_record.enrolled_at.isoformat() if new_record.enrolled_at else None,
            message=f"报名成功，已分配 {total_lessons} 课时",
        )

    @tool(ToolMeta(
        name="drop_course",
        description="学生退课",
        parameters={"student_id": {"type": "integer"}, "course_id": {"type": "integer"}},
        require_permission=True,
    ))
    async def drop_course(self, ctx: CTX, student_id: int, course_id: int) -> ServiceResult:
        dao: StudentCourseDao = get_dao(ctx, self.dao_class)
        record = await dao.get_by_student_and_course(student_id, course_id)
        if not record:
            return ServiceResult.error(message="未选该课程", code=404, trace_id=ctx.trace_id)
        await dao.soft_delete(record.id)
        return ServiceResult.ok(data=None, trace_id=ctx.trace_id, message="退课成功")