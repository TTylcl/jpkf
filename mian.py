from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import traceback

# ... existing code ...
# ！！！所有自定义导入全部注释掉，避免外部依赖报错
# import sys
# from pathlib import Path
# sys.path.append(str(Path(__file__).resolve().parent.parent))
# from utils.logger import add_log
# from core.llm_client import LLMClient
# from core import settings
# from core.graph.state import ChatState


# ChatState直接写在当前文件里，避免导入错误
class ChatState(BaseModel):
    user_id: str = Field(..., description="请求人身份", examples=["张三妈妈"])
    user_input: str = Field(..., description="用户输入", examples=["可以帮我查数学课剩余课时吗？"])
    generated_reply: str = Field(None, description="历史回复")


fake_user_data = {
    "张三妈妈": {"孩子姓名": "张三", "英语课时": 12, "数学课时": 8},
    "李四爸爸": {"孩子姓名": "李四", "英语课时": 5, "数学课时": 15}
}

app = FastAPI(title="测试版本")

# 全局异常捕获：所有错误都会直接返回到响应里，不用猜
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # 把错误栈完整返回给前端
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "msg": "服务内部错误",
                "error_detail": str(e),
                "traceback": traceback.format_exc()
            }
        )

# 先把LLM、日志都注释掉，只保留最基础逻辑
@app.post("/chat", summary="测试AI对话")
async def test_chat(req: ChatState):
    try:
        # add_log先注释，避免日志工具报错
        # add_log(f"收到用户【{req.user_id}】的请求：{req.user_input}")
        
        print(f"收到的user_id：{repr(req.user_id)}")
        print(f"字典键：{list(fake_user_data.keys())}")
        
        user_info = fake_user_data.get(req.user_id)
        if not user_info:
            return {"code": 404, "msg": f"未找到用户【{req.user_id}】"}
        
        context = f"用户档案：{req.user_id} | 孩子：{user_info['孩子姓名']} | 数学课时：{user_info['数学课时']}节"
        prompt = f"你是客服，根据下面信息回答：\n{context}\n问题：{req.user_input}"
        
        # LLM调用先注释，避免LLM初始化/调用报错
        # llm_client.call(prompt)
        
        # 先直接返回拼接好的prompt，确认逻辑正常
        return {"code":200, "data": {"generated": f"测试正常，拼接的prompt是：{prompt}"}}
    
    except Exception as e:
        # 接口内部错误也返回细节
        return {"code": 500, "msg": "接口逻辑错误", "error": str(e), "traceback": traceback.format_exc()}


@app.get("/",summary="健康检查")
def health_check():
    return {"code":200,"msg":"服务正常"}

if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        reload=False, # 关掉热重载避免吞错误
        log_level="debug"
    )