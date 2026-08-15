"""
schemas/schedule_schemas.py
排课查询相关数据模型
Schema层：参数验证 + 结构化输出
"""

from pydantic import BaseModel, Field



class ScheduleQuery(BaseModel):
    """排课查询入参"""
    parent_id: int = Field(..., gt=0, description="家长用户ID")
    day_of_week: int = Field(
        default=0,
        ge=0, le=7,
        description="星期几：1=周一~7=周日，0=由服务端自动计算今天"
    )


class ScheduleItem(BaseModel):
    """单条排课记录"""
    schedule_id: int = Field(description="排课ID")
    course_id: int = Field(description="课程ID")
    course_name: str = Field(default="", description="课程名称")
    teacher_id: int = Field(description="教师ID")
    teacher_name: str = Field(default="", description="教师姓名")
    student_names: str = Field(default="", description="该时段上课的学生姓名，多人用逗号分隔")
    student_count: int = Field(default=0, description="该时段上课的学生数量")
    day_of_week: int = Field(description="星期几：1=周一...7=周日")
    start_time: str = Field(description="上课时间，如14:00")
    end_time: str = Field(description="下课时间，如15:30")
    classroom: str | None = Field(default=None, description="教室")


class ScheduleResult(BaseModel):
    """排课查询结果"""
    items: list[ScheduleItem] = Field(default_factory=list, description="课程列表")