
#/schemas/chat_schemas.py
from typing import Optional # 导入Optional
from pydantic import BaseModel,ConfigDict,Field


#对话请求体
class ChatRequest(BaseModel):
    """对话请求体"""
    model_config = ConfigDict(extra="allow") 
    
    message : str = Field(...,description="用户输入")
    user_id: str = Field(...,description="用户ID")  
    #agent_role: str = Field(default='customer_service_agent',description="智能体角色:customer_service_agent/edu_admin_agent/teacher_agent/student_agent")
    thread_id: Optional[str] = Field(default=None,description="会话ID,多轮对话传入")
    wx_openid: str = Field(default="", description="微信openid，群聊场景必传")


#对话响应体
class ChatResponse(BaseModel):
    """对话响应体"""
    model_config = ConfigDict(extra="allow")
    code: int = Field(default=200, description="状态码，0或200=成功，其他=错误")
    message: str = Field(default="success", description="提示信息")
    thread_id: str = Field(default="", description="会话ID，前端需保存并在后续请求中传入")
    reply: str = Field(default="", description="AI 回复内容")
   


