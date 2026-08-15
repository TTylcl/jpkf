import sys
sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# 路由
from api.routers.ai_chat_router import router as ai_chat_router
from api.routers.debug_router import router as debug_router
# 创建图
from core.graph.builder import build_agent_graph
from core.database import AsyncDatabase
from core.scheduler import init_scheduler, shutdown_scheduler
from core import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)

    # 自动建表（确保所有模型导入后再 create_all）
    from dal.models.base_model import Base
    from dal.models import __init__ as _  # 触发所有模型导入
    async with AsyncDatabase.get_session() as session:
        conn = await session.connection()
        await conn.run_sync(Base.metadata.create_all)
    print("=========✅ 数据库表初始化完成========")

    # 启动时：构建 LangGraph ReAct 循环
    graph = build_agent_graph()

    app.state.graph = graph

    print("=========✅ Graph初始化完成========")

    # 启动后台调度器（每分钟扫描排课，自动生成待办+通知）
    init_scheduler()

    yield
    # 停止时清理资源
    shutdown_scheduler()
    print("=========🛑 Graph清理完成========")


#初始化FastAPI服务
app = FastAPI(
    title="客服系统",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)
#注册路由
app.include_router(ai_chat_router,prefix="/api")
app.include_router(debug_router,prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")

#健康检测
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)