import sys
from pathlib import Path
from loguru import logger
from typing import List, Dict, Optional, Any
import time
from core import settings
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
    format="{time:HH:mm:ss} | {level: <8} | {extra[module]} | {message}",
    rotation=settings.LOG_ROTATION,     
    retention=settings.LOG_RETENTION,    
    encoding=settings.ENCODING,
    
    level=settings.LOG_DEFAULT_LEVEL
)
def add_log( level: str, message: str, module: str = "systeam", **kwargs) -> None:
    """添加日志"""

    try:
        normalized_level = str(level).strip().upper()
    except Exception:
        normalized_level = "unknown"


    if normalized_level not in settings.LOG_LEVEL:
        # 输出错误日志 
        logger.bind(module=module, **kwargs).warning(f"Invalid level '{level}', fallback to info.")    
        normalized_level = "INFO"
            
    # 获取当前时间
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    record = {"time": now, "level": normalized_level, "module": module, **kwargs}
   

    if normalized_level == "ERROR":
        logger.bind(module=module, **kwargs).error(message)
    logger.bind(module=module,**kwargs).log(normalized_level, message)

