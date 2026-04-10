from fastapi import FastAPI
from pydantic import BaseModel,Field
import uvicorn
import aiohttp

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.logger import add_log
from core.llm_client import LLMClient
from core import settings

#初始化FastAPI服务
app = FastAPI(
    title="客服系统",
    version="1.0.0",
    description="2026晓雪-多模态教育客服系统"
)

#初始化LLMCLIent
llm_client = LLMClient()


@app.get("/",summary="健康检查接口")
def health_check():
    return {"code":200,"msg":"服务正常"}
if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=settings.WS_PORT,
        reload=True, # 开发环境开热重载，改代码自动重启
        log_level=settings.API_LEVEL,#
         # 启动进程数
    )