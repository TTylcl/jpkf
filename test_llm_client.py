from fastapi import FastAPI
from pydantic import BaseModel,Field
import uvicorn


import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.logger import add_log
from core.llm_client import LLMClient
from core import settings
from core.graph.state import ChatState
import asyncio


fake_user_data = {
    "张三妈妈": {"孩子姓名": "张三", "英语课时": 12, "数学课时": 8},
    "李四爸爸": {"孩子姓名": "李四", "英语课时": 5, "数学课时": 15}
}
#初始化FastAPI服务
app = FastAPI(
    title="客服系统",
    version="1.0.0",
    description="2026晓雪-多模态教育客服系统"
)
#全局唯一实例化

#初始化LLMCLIent
llm_client = LLMClient()

@app.post("/chat", summary="测试AI对话")
async def test_chat(req: ChatState):
    add_log(f"收到用户【{req.user_id}】的请求：{req.user_input}")
    user_info = fake_user_data.get(req.user_id)
    # 👇 加这3行调试，请求后看控制台输出
    print(f"收到的user_id：{repr(req.user_id)}") # repr会显示隐藏的空格/特殊字符
    print(f"字典的所有键：{list(fake_user_data.keys())}")
    print(f"匹配结果：{user_info}")
    if not user_info:
        return {"code": 404, "msg": f"未找到用户【{req.user_id}】的档案，请核对身份"}
     # 构建上下文
    context = (
        f"📊 用户档案：{req.user_id} | "
        f"孩子：{user_info['孩子姓名']} | "
        f"英语课时：{user_info['英语课时']}节 | "
        f"数学课时：{user_info['数学课时']}节"
    )
    
    prompt = (
        f"你是一名教育客服。请严格根据以下背景信息回答用户问题：\n"
        f"{context}\n\n"
        f"用户问题：{req.user_input}\n\n"
        f"请用中文回复，保持专业且友好。"
    )
    
    try:
        # 异步调用LLM（假设LLMClient支持异步或使用线程池）
        # 如果llm_client.call是同步的，使用线程池避免阻塞
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: llm_client.call(prompt)
        )
        
        add_log(f"用户【{req.user_id}】的回复：{response}")
        
        return {
            "code": 200,
            "data": {
                "user_input": req.user_input,
                "generated": response,
                "user_info": user_info
            }
        }
        
    except Exception as e:
        add_log(f"LLM调用失败：{str(e)}", level="ERROR")
        return {
            "code": 500,
            "msg": f"AI服务暂时不可用：{str(e)}"
        }

@app.get("/",summary="健康检查接口")
def health_check():
    return {"code":200,"msg":"服务正常"}
# 获取可用用户列表
@app.get("/users", summary="获取可用用户列表")
def get_users():
    return {
        "code": 200,
        "data": {
            "available_users": list(fake_user_data.keys()),
            "total": len(fake_user_data)
        }
    }
if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,#settings.WS_PORT,
        reload=True, # 开发环境开热重载，改代码自动重启
        log_level="debug",#
         # 启动进程数
    )
