# main.py 第一步的伪代码结构，自己补
# 1. 导入官方依赖
from fastapi import FastAPI
from pydantic import BaseModel, Field # 用来做参数校验
import uvicorn
# 2. 导入你自己写的核心模块（路径要对，和test_core.py里的导入路径一样）
from utils.logger import logger # 你之前写的日志工具
from core.llm_client import LLMClient
from config.settings import settings # 你之前写的配置
# 3. 初始化FastAPI服务
app = FastAPI(
    title="情感陪伴AI对话接口",
    version="1.0.0",
    description="2026求职项目-多模态情感陪伴系统"
)
# 4. 全局初始化LLMClient（🔥 重要：只初始化一次，所有请求复用，不然熔断计数器会失效）
llm_client = LLMClient()
logger.info("✅ 服务启动，LLMClient初始化完成")
# 5. 先写一个健康检查接口（企业级必备，后面部署运维探活用）
@app.get("/health", summary="健康检查接口")
def health_check():
    return {"code": 200, "msg": "服务正常运行"}
# 6. 本地启动入口
if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=settings.server_port, # 从你之前写的配置里读端口，不用硬编码
        reload=True # 开发环境开热重载，改代码自动重启
    )