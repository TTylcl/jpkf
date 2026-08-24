# /core/graph/tools/loader.py
"""
工具加载器
职责：自动发现并加载所有 Service 的 @tool 方法，转换为 LangChain BaseTool 列表。
"""
from __future__ import annotations
import inspect
from typing import Any, Type
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model, Field


# ✅ 从 context_binder.py 导入
from core.graph.tools.context_binder import bind_ctx_to_tool
from core.service.models import AGENT_PERMISSIONS_MATRIX

# 导入所有 Service 类
from service.user_service import UserService
from service.course_service import CourseService
from service.student_course_service import StudentCourseService
from service.parent_student_service import ParentStudentService
from service.schedule_service import ScheduleService
from service.pre_schedule_service import PreScheduleService
from service.rag_service import RagService
from service.lesson_consumption_service import LessonConsumptionService
from service.teacher_todo_service import TeacherTodoService
from service.notification_service import NotificationService
from utils.logger import add_log


# ✅ 所有需要暴露给 Agent 的 Service 实例（单例）
SERVICE_INSTANCES = [
    UserService(),
    CourseService(),
    StudentCourseService(),
    ParentStudentService(),
    ScheduleService(),
    PreScheduleService(),
    RagService(),
    LessonConsumptionService(),   # 消课：教师确认消耗课时
    TeacherTodoService(),          # 待办：教师查看今日待消课清单
    NotificationService(),         # 通知：查通知、标记已读
]


# ✅ 参数类型映射：将字符串类型转为 Python 类型
TYPE_MAP: dict[str, Type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def _build_args_schema(
    func_name: str,
    parameters: dict[str, dict]
) -> Type[BaseModel] | None:
    """
    根据参数描述构建 Pydantic 模型（输入 schema）。
    带 description，LLM 能看懂每个参数是什么
    """
    if not parameters:
        return None  # 无参数工具
    
    fields: dict[str, tuple[Type, Any]] = {}
    
    for param_name, info in parameters.items():
        param_type_str = info.get("type", "string")
        param_type = TYPE_MAP.get(param_type_str, str)
        description = info.get("description", "")

        # ✅ 区分 required vs optional：有 "default" key → 可选；无 → 必填
        if "default" in info:
            fields[param_name] = (param_type, Field(info["default"], description=description))
        else:
            fields[param_name] = (param_type, Field(..., description=description))
    
    # 生成唯一的模型名，避免冲突
    schema_name = f"{func_name}_input"
    return create_model(schema_name, **fields)


def build_langchain_tools(agent_role: str | None = None,tool_names: list[str] | None = None) -> list[StructuredTool]:
    """
    遍历所有 Service 实例，收集所有 @tool 方法，返回 LangChain 工具列表。

    Args:
        agent_role: 可选，按角色过滤工具（None = 不过滤，返回全部）
        tool_names: 可选，指定工具名称列表（None = 使用所有工具）
    """
    tools: list[StructuredTool] = []
    permissions = AGENT_PERMISSIONS_MATRIX.get(agent_role, {}) if agent_role else None

    for service in SERVICE_INSTANCES:
        resource = getattr(service, "resource", None)  # Service 的资源名

        for method_name, method in inspect.getmembers(service, predicate=inspect.ismethod):
            # 检查是否有 __tool_meta__ 属性
            if not hasattr(method, "__tool_meta__"):
                continue

            meta = method.__tool_meta__
            tool_name = meta.name

            # ✅ 按 tool_names 白名单过滤（意图级别，比 agent_role 更细粒度）
            if tool_names is not None and tool_name not in tool_names:
                continue
            if permissions is not None:
                allowed_ops = permissions.get(resource, [])
                if tool_name not in allowed_ops:
                    continue

            description = meta.description
            parameters = meta.parameters

            # 1. 构建输入 schema（带 description）
            args_schema = _build_args_schema(tool_name, parameters)

            # 2. ✅ 从 context_binder.py 导入的包装方法
            wrapped_method = bind_ctx_to_tool(method)

            # 3. 创建 StructuredTool（附带 resource 元数据）
            tool = StructuredTool(
                name=tool_name,
                description=description,
                args_schema=args_schema,
                coroutine=wrapped_method,  # 符合 LangChain 规范
                func=None,
                metadata={"resource": resource},  # ✅ 用于权限过滤
            )
            tools.append(tool)

    add_log("INFO", f"加载 {len(tools)} 个工具 (agent_role={agent_role or 'all'})", module="tools")
    return tools


__all__ = ["build_langchain_tools"]


# 单独运行测试
if __name__ == "__main__":
    tools = build_langchain_tools()