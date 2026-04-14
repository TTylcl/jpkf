
from pydantic import BaseModel,Field
from typing import Optional

# core\graph\state.py
class ChatState(BaseModel):
    # 用户身份（用于查询用户档案，模拟真实场景）
    user_id: str = Field(...,  # 补回这个字段！
                         description="请求人身份：",
                         examples=["张三妈妈"])
    # 用户输入
    user_input: str = Field(..., 
                            description="用户输入",
                            examples=[
                                "可以帮我查周四的课吗？" 
                            ])
    # 生成回复
    generated_reply: Optional[str] = Field(
        "",  # 建议默认值用空字符串，和你之前的代码逻辑更配
        description="历史AI回复用于多轮对话",
        examples=["当然可以，请提供具体课程的名称或者日期。"]
    )
