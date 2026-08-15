#core/service/models.py
"""
Service层数据模型：统一返回格式 + 全局权限矩阵
【权限管控的基础，所有业务的权限都从这里来】
"""
from pydantic import BaseModel,Field
from typing import Any, Dict, Optional


class ServiceResult(BaseModel):
    """
    Service层所有方法只能返回这个格式
    
    【设计目的】
    ✅ 防止AI乱返回格式，上层处理统一
    ✅ 自动带trace_id，出问题能追溯
    ✅ 统一的成功/失败判断，不用猜
    """
    
    success: bool = Field(..., description="是否成功") #
    #状态码
    code: int = Field(..., description="状态码,0表示成功，非0表示失败，具体含义由业务定义")
    #提示信息
    message: str = Field(..., description="提示信息") 
    #业务数据
    data: Any = Field(None, description="业务数据")
    #trace_id
    trace_id: str = Field(..., description="全链路追踪ID")
    model_config = {
        #"frozen": True,  # ✅ 拦截AI幻觉
        "arbitrary_types_allowed": True  # 允许 session 这种非 pydantic 类型
    }
    @classmethod
    def ok(cls,data:Any=None,message:str="success",trace_id:str=''):
        """
        c创建成功返回
        【参数】
        cls: ServiceResult 类本身，用于创建对象
        data: Any = None   # 返回的业务数据
        message: str = "success"  # 提示信息，默认为 "success"
        trace_id: str = '' # 全链路追踪ID
        【返回】
        ServiceResult(success=True, code=0, message=message, data=data,trace_id=trace_id)
        【使用】
        return ServiceResult.ok(data={"id": 123}, message="创建成功")
        """
        return cls(success=True, code=0, message=message, data=data,trace_id=trace_id)
    

    def __str__(self) -> str:
        """返回 LLM 友好的自然语言，ToolNode 做 str(result) 时自动调用。

        成功时展开 data（Pydantic 模型序列化为 JSON，其他类型直接转字符串），
        失败时按 code 格式化为带 emoji 的中文提示。

        self.success / self.code / self.data / self.trace_id 属性不受影响，
        程序侧仍可正常读取。
        """
        if self.success:
            if self.data is not None:
                if isinstance(self.data, BaseModel):
                    return self.data.model_dump_json(indent=2)
                return str(self.data)
            return self.message

        # 失败时按错误码格式化
        if self.code == 403:
            return f"❌ 权限不足：{self.message}"
        if self.code == 404:
            return f"❌ 资源不存在：{self.message}"
        if self.code == 409:
            return f"❌ 操作冲突：{self.message}"
        if self.code == 500:
            return f"❌ 系统异常：{self.message}"
        return f"❌ 操作失败（{self.code}）：{self.message}"

    @classmethod
    def error(cls,message:str,code:int=-1,data:Any=None,trace_id:str=''):
        """
        创建失败返回
        【参数】
        message: str = "创建失败"  # 提示信息，默认 "创建失败"
        code: int = -1  # 状态码，默认 -1
        data: Any = None   # 错误信息
        trace_id: str = '' # 全链路追踪ID
        【返回】
        ServiceResult(success=False, code=code, message=message, data=data, trace_id=trace_id)
        【使用】
        return ServiceResult.error(message="创建失败", code=-1, data={"reason": "参数错误"},    trace_id=trace_id)
        """
        return cls(success=False, code=code, message=message, data=data,trace_id=trace_id)
"""
权限矩阵
【设计目的】
✅ 权限管控的基础，所有业务的权限都从这里来
【设计原则】
✅ 统一权限矩阵，避免重复定义
✅ 细粒度权限控制，支持不同角色的不同操作
 customer_service_agent：客服智能体（微信小程序用），只能查，不能改
- edu_admin_agent：教务智能体（后台管理用），可以查+改
- 每个业务领域允许的操作白名单，不在白名单里的操作直接拦截
"""
AGENT_PERMISSIONS_MATRIX = {
    "customer_service_agent": {
        "user": ["query_users", "get_user", "get_user_by_username", "count_users"],
        "course": ["query_courses", "get_course", "get_course_by_code"],
        "schedule": [ "query_schedules","get_today_schedules","check_teacher_availability"],
        "student_course": ["get_my_courses", "get_course_students", "check_enrollment"],
        "parent_student": ["get_my_children", "get_student_parents",
                       "get_child_courses", "get_child_schedules"],
        "pre_schedule": ["submit_pre_schedule", "get_my_submissions"],
        "rag": ["rag_search"],
        # 消课模块：家长只能查看消课记录和通知，不能执行消课
        "lesson_consumption": [],
        "teacher_todo": [],
        "notification": ["get_my_notifications", "mark_notification_read", "mark_all_notifications_read"],
    },
    "edu_admin_agent": {
        "user": ["query_users", "get_user", "get_user_by_username", "count_users",
                 "create_user", "update_user", "delete_user"],
        "course": ["query_courses", "get_course", "get_course_by_code",
                   "create_course", "update_course", "delete_course"],
        "schedule":["query_schedules","get_today_schedules","create_schedule","delete_schedule",],
        "student_course": ["get_my_courses", "get_course_students", "check_enrollment",
                       "enroll_student", "drop_course"],
        "parent_student": ["get_my_children", "get_student_parents",
                       "bind_parent_student", "unbind_parent_student",
                       "get_child_courses", "get_child_schedules"],
        "pre_schedule": ["submit_pre_schedule", "get_my_submissions",
                       "review_pre_schedule", "get_pending_reviews"],
        "rag": ["rag_search"],
        # 消课模块：管理员拥有全部权限
        "lesson_consumption": ["consume_lesson", "query_consumption_history"],
        "teacher_todo": ["get_my_todos", "mark_todo_done"],
        "notification": ["get_my_notifications", "mark_notification_read", "mark_all_notifications_read"],
    },
    "teacher_agent": {
        "user": ["query_users", "get_user", "get_user_by_username"],
        "course": ["query_courses", "get_course", "get_course_by_code",
                   "get_course_students", "check_enrollment"],
        "schedule":["query_schedules","get_today_schedules","create_schedule","delete_schedule",],
        "student_course": ["get_course_students", "check_enrollment"],
        "pre_schedule": ["review_pre_schedule", "get_pending_reviews"],
        "rag": ["rag_search"],
        # 消课模块：教师可以消课、查看自己的待办和通知
        "lesson_consumption": ["consume_lesson", "query_consumption_history"],
        "teacher_todo": ["get_my_todos", "mark_todo_done"],
        "notification": ["get_my_notifications", "mark_notification_read", "mark_all_notifications_read"],
    },
    "student_agent": {
        "user": ["get_user"],
        "course": ["query_courses", "get_course", "get_course_by_code",
                   "get_my_courses", "check_enrollment"],
        "schedule": [ "query_schedules","get_today_schedules","check_teacher_availability"],
        "student_course": ["get_my_courses", "check_enrollment"],
        "rag": ["rag_search"],
        # 消课模块：学生只能查看通知（上课提醒、消课通知）
        "lesson_consumption": [],
        "teacher_todo": [],
        "notification": ["get_my_notifications", "mark_notification_read", "mark_all_notifications_read"],
    },
}
def check_permission(agent_role: str, resource: str, operation: str) -> bool:
    """
    检查权限
    【参数】
    agent_role: str  # 角色名称，如 customer_service_agent
    resource: str  # 资源名称，如 user
    operation: str  # 操作名称，如 get_by_id
    【返回】 
    True=有权限，False=无权限
    【使用】
    if check_permission("customer_service_agent", "user", "get_by_id"):
    """
    if agent_role not in AGENT_PERMISSIONS_MATRIX:
        return False
    resource_permissions = AGENT_PERMISSIONS_MATRIX[agent_role].get(resource, [])
    return operation in resource_permissions

def get_allowed_operations(agent_role: str, resource: str) -> list:
    """
    获取允许的操作
    【参数】
    agent_role: str  # 角色名称，如 customer_service_agent
    resource: str  # 资源名称，如 user
    【返回】
    允许的操作列表，如 ["get_by_id", "list"]
    【使用】
    allowed_operations = get_allowed_operations()
    """
    if agent_role not in AGENT_PERMISSIONS_MATRIX:
        return []
    return AGENT_PERMISSIONS_MATRIX[agent_role].get(resource, [])

__all__ = [
    "ServiceResult",
    "check_permission",
    "AGENT_PERMISSIONS_MATRIX",
    "get_allowed_operations"
]