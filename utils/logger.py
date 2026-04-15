import sys
from pathlib import Path
from loguru import logger
from typing import List, Dict, Optional, Any
import time
from core import settings
from typing import TYPE_CHECKING # 用于类型检查
if TYPE_CHECKING: # 类型检查
    from core.context import AgentContext # 导入数据类模块


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


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
    Path(settings.LOG_DIR) /"agent_{time:YYYY-MM-DD}.log",
    serialize=True,        # 输出 JSON 格式（便于解析）
    #format="{time:HH:mm:ss} | {level: <8} | {extra[module]} | {message}",
    rotation=settings.LOG_ROTATION,     
    retention=settings.LOG_RETENTION,    
    encoding=settings.ENCODING,
    
    level=settings.LOG_DEFAULT_LEVEL
)
def add_log( level: str, message: str, module: str = "system", ctx:Optional["AgentContext"]=None,**kwargs) -> None:
    """添加日志"""

    try:
        normalized_level = str(level).strip().upper()
    except Exception:
        normalized_level = "unknown"


    if normalized_level not in settings.ALLOWED_LEVELS:
        # 输出错误日志 
        logger.bind(module=module, **kwargs).warning(f"Invalid level '{level}', fallback to info.")    
        normalized_level = "INFO"
    #统一处理
    # 2. 构造统一结构化日志记录，和全局日志的字段100%对齐
    log_record = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "level": normalized_level,
        "module": module,
        "message": message,
        **kwargs # 扩展字段：比如请求ID、用户标识，按需加
    }
    #如果传了ctx,先把数据存储起来       
    if ctx: 
        ctx.logs.append(log_record) 
        if normalized_level == "ERROR":
            ctx.error_logs.append(log_record)

    getattr(logger, normalized_level.lower())(f"[{module}] {message}", **log_record)
    

