# \core\context.py
#导入数据类模块

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import sys
from pathlib import Path
from loguru import logger
import time
from core import settings
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

#定义数据类
@dataclass 
class AgentContext:
    """
        定义一个数据类，用于存储插件上下文信息

    全局共享上下文
    作用：贯穿 Agent / 流水线 / 插件 / 熔断 / 异常 的所有数据载体
    """
    agent_id: str
    agent_name: str

    """
    输入数据
    用户的原始请求（如自然语言指令）
    上下文参数
    任务目标描述
    前置步骤的输出结果
    """
    task_input: Optional[Any] =None

    """
    输出数据
    任务结果
    任务结果描述
    任务结果附件
    """
    task_result: Optional[Any] =None




    #----日志---
    #日志记录
    logs: List[Dict] = field(default_factory=list)
    ## 错误日志单独存一份，方便快速获取
    error_logs: List[Dict[str, Any]] = field(default_factory=list)

    # 熔断状态
    # --------------------------
    circuit_status: str = "closed"  # closed / open / half_open

    # 拓扑信息
    # --------------------------
    #"graph" / "dag"：有向无环图，支持分支、并行、条件跳转
    #"tree"：树状结构，适用于分治类任务
    #star"：中心节点协调多个并行子任务
    topology_type: str = "linear"  #线性
    topology_nodes: List[str] = field(default_factory=list)

    # 插件状态 & 记忆 & 元数据
    plugin_status: Dict[str, bool] = field(default_factory=dict)
    plugin_memory: Dict[str, Any] = field(default_factory=dict)
    plugin_meta: Dict[str, Any] = field(default_factory=dict)


    def __post_init__(self):
        """
        初始化日志
        """
        
        # 清空日志
        logger.remove() 
        # 控制台输出（带颜色）
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[module]}</cyan> | {message}",
            level=settings.LOG_DEFAULT_LEVEL
        )
        # 文件输出（按天分割，自动清理）
        logger.add(
            settings.LOG_DIR / f" agent_{time:YYYY-MM-DD}.log",
            serialize=True,        # 输出 JSON 格式（便于解析）
            #format="{time:HH:mm:ss} | {level: <8} | {extra[module]} | {message}",
            rotation=settings.LOG_ROTATION,     
            retention=settings.LOG_RETENTION,    
            encoding=settings.ENCODING,
            
            level=settings.LOG_DEFAULT_LEVEL
        )
    def add_log(self, level: str, message: str, module: str = "systeam", **kwargs) -> None:
        """添加日志"""
        
        try:
            normalized_level = str(level).strip().upper()
        except Exception:
            normalized_level = "UNKNOWN"
       

        if normalized_level not in settings.LOG_LEVELS:
            # 输出错误日志 
            logger.bind(module=module, **kwargs).warning(f"Invalid level '{level}', fallback to INFO.")    
            normalized_level = "INFO"
                
        # 获取当前时间
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        record = {"time": now, "level": normalized_level, "module": module, **kwargs}
        self.logs.append(record)
   
        if normalized_level == "ERROR":
            self.error_logs.append(record)
        logger.bind(module=module,**kwargs).log(normalized_level, message)
    # 获取日志
    def get_all_logs(self) -> List[Dict]:
        """获取全部日志"""
        return self.logs
    def get_error_logs(self) -> List[Dict]:
        """获取错误日志"""
        return self.error_logs
    def clear_logs(self) -> None:
        """清空日志"""
        self.logs.clear()
        self.error_logs.clear()



