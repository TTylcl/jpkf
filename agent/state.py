"""
功能：Agent 状态定义
  职责：定义 AgentState，存储对话历史和用户标识  说明：
  - messages 字段用 add_messages 合并消息历史
  - 只存用户标识（user_id、user_role、agent_role），不存完整 CTX
  - 完整 CTX 每次调用时重建
  - total=False 允许子图/路由使用可选字段
"""
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict,total=False): # total=False 允许子图/路由使用可选字段
    """
    包含：
      messages: 消息历史，用 LangChain 自带的 add_messages 合并
      user_id: 用户 ID（用于重建 CTX）
      user_role: 用户角色（用于权限控制）
      agent_role: Agent 角色（用于决定可用工具集）

      子图/路由扩展字段（可选）：
      intent: 意图分类结果（parent_schedule / parent_course / general）
      day_of_week: 解析后的星期几（1-7），排课子图使用
      children_data: 预取的孩子列表 [{"student_id": int, "student_name": str}, ...]
      permission_denied: 权限校验拒绝标记（True=拒绝，后续节点短路）
    """
    # 消息历史：自动合并，不覆盖
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 用户标识：用于重建 CTX，不存完整 CTX
    user_id: int
    user_role: str
    agent_role: str


    # 子图/路由扩展字段（可选）：
    intent: str                                          # 意图分类结果
    day_of_week: int                                    # 排课用：解析后的星期几（1-7）
    children_data: list[dict[str, int | str]]           # 预取的孩子列表
    permission_denied: bool                              # 权限校验拒绝标记