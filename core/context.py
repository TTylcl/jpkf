"""
CTX - 双智能体教务系统统一上下文
【pydantic 版 + 微信适配】

【核心设计原则（8项，去掉3项过度设计）】
1. ✅ 字段精简・幻觉免疫前置：只放必要字段
2. ✅ 显式传递・全链路闭环：作为参数传，不用全局单例
3. ✅ 异步友好・无阻塞适配：pydantic 异步友好
4. ✅ 简单易用・边界内可控：结构清晰，职责单一
5. ✅ 权限安全・原生前置拦截：agent_role + user_role 双层权限
6. ✅ 业务绑定・权责边界固化：双智能体角色固定
7. ✅ 不可篡改・幻觉免疫：frozen=True，AI 不能改
8. ✅ 全链路可追溯：trace_id + request_id
9. ✅ 生态兼容：pydantic 原生适配 FastAPI/微信生态
10. ✅ 可扩展：预留 extra 字段
"""
#/core/context.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


#runtime 上下文
class AgentContext(BaseModel):
    """LangGraph Runtime Context Schema - 只映射config里的字段"""
    user_id: str = ""          # 用户ID
    agent_role: str = ""        # 智能体角色
    user_role: str = ""       # 用户角色
    trace_id: str = ""        # 全链路追踪ID
    wx_openid: str = ""       # 微信 openid




#service 上下文
class CTX(BaseModel):
    """
    上下文对象
    
    【CRITICAL】frozen=True，创建后不可修改！
    AI 绝对不能修改 CTX 里的任何字段，只能读
    """
    
    model_config = {
        "frozen": True,  # ✅ 不可篡改，幻觉免疫核心机制
        "arbitrary_types_allowed": True  # 允许 session 这种非 pydantic 类型
    }
    
    # ==========================================
    # 🔐 权限核心字段（不可篡改）
    # ==========================================
    
    agent_role: str = Field(..., description="智能体角色：customer_service_agent / edu_admin_agent")
    user_id: int = Field(..., gt=0, description="系统内部用户ID，必须>0，拦截幻觉")
    user_role: str = Field(..., description="用户角色：student / teacher / admin")
    
    # ==========================================
    # ✨ 微信用户信息
    # ==========================================
    
    wx_openid: str = Field("", description="微信 openid，空字符串表示非微信用户")
    wx_unionid: Optional[str] = Field(None, description="微信 unionid，可选")
    wx_session_key: Optional[str] = Field(None, description="微信会话密钥，可选，保密字段")
    
    # ==========================================
    # 🔍 追踪审计字段
    # ==========================================
    
    trace_id: str = Field(..., description="全链路追踪ID")
    request_id: str = Field(None, description="单次请求ID")
    
    # ==========================================
    # 🗄️ 数据库连接
    # ==========================================
    
    session: Any = Field(..., description="数据库 session")
    
    # ==========================================
    # 🌐 辅助字段
    # ==========================================
    
    client_ip: str = Field("127.0.0.1", description="客户端IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    
    # ==========================================
    # 🚀 预留扩展字段（"领域化可扩展"简化版）
    # ==========================================
    
    extra: Dict[str, Any] = Field(default_factory=dict, description="预留扩展字段，临时字段先放这里")