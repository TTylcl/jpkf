# \core\context.py
#导入数据类模块
from typing import List, Dict, Optional,Any

from pydantic import BaseModel,Field
import sys
from pathlib import Path
from loguru import logger
import time
from core import settings


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

#定义数据类

class AgentContext(BaseModel):
    """
        定义一个数据类，用于存储插件上下文信息

    全局共享上下文
    作用：贯穿 Agent / 流水线 / 插件 / 熔断 / 异常 的所有数据载体
    """
    agent_id: str #智能体ID
    agent_name: str #

    """
    输入数据
    用户的原始请求（如自然语言指令）
    上下文参数
    任务目标描述
    前置步骤的输出结果
    """
    user_id:Optional[str] = None #用户ID
    user_input: Optional[Any] =None  #用户原始请求
    user_info: Optional[Dict] = None #用户信息
    final_params: Optional[Dict] = None #上下文参数
    """
    输出数据
    任务结果
    任务结果描述
    任务结果附件
    """
    task_result: Optional[Any] =None #存LLM回复





    #----日志---
    #日志记录
    logs: List[Dict] = Field(default_factory=list)
    ## 错误日志单独存一份，方便快速获取
    error_logs: List[Dict[str, Any]] = Field(default_factory=list)

    # 熔断状态
    # --------------------------
    circuit_status: str = "closed"  # closed / open / half_open

   
    # 插件状态 & 记忆 & 元数据
    plugin_status: Dict[str, bool] = Field(default_factory=dict)
    plugin_memory: Dict[str, Any]  = Field(default_factory=dict)
    plugin_meta: Dict[str, Any]  = Field(default_factory=dict)

    #LLMclient
    llm_client: Any 
    """
    def add_simple_log(self, log_level: str, message: str, **kwargs)-> None:
     
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_entry = {
            "time": now,
            "level": log_level,
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)
        if log_level == "ERROR":
            self.error_logs.append(log_entry)
    # 允许LLMClient这类非Pydantic类型的字段
    """
    class Config:
        arbitrary_types_allowed = True


