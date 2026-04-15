
from pydantic import BaseModel,Field
from typing import Optional,List
from core.context import AgentContext
# core\graph\state.py
class ChatState(BaseModel):
    ctx:AgentContext = Field(..., 
                           description="会话上下文",
                           examples=[
                               {
                                   "user_id": "张三妈妈",
                                   "user_input": "可以帮我查周四的课吗？"
                                   
                               }
                           ])
    messages: List[dict] = Field(
        default_factory=list,
        description="对话历史消息，格式为[{\"role\": \"user/assistant\", \"content\": \"xxx\"}]",
        examples=[[{"role": "user", "content": "我孩子剩下多少数学课"}]]
    )
    # 生成回复
    generated_reply: str = Field(
        "",  # 建议默认值用空字符串，和你之前的代码逻辑更配
        description="历史AI回复用于多轮对话",
        examples=["当然可以，请提供具体课程的名称或者日期。"]
    )
    # 👉 如果需要用到course_info，在这里加字段，不要直接用get访问
    course_info: Optional[dict] = Field(
        default=None,
        description="查询到的结构化课程数据"
    )
    class Config:
        arbitrary_types_allowed = True