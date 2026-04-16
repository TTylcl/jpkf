

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))


from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware  # 【新增】导入跨域中间件
from core.get_llm_client import get_llm_client
# 添加跨域中间件



from utils.logger import add_log

from core.graph.state import ChatState




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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)
#全局唯一实例化
#初始化LLMCLIent


@app.post("/chat", summary="测试AI对话")
async def test_chat(req: ChatState):
        print("______________________________________")
        # 调试：打印原始请求体
        try:
            # 1. 检查用户是否存在
            user_info = fake_user_data.get(req.ctx.user_id)
            if not user_info:
                add_log('ERROR', f"未找到用户【{req.ctx.user_id}】的档案，请核对身份")
                return {
                    "code": 404,
                    "msg": f"未找到用户【{req.ctx.user_id}】的档案，请核对身份",
                    "available_users": list(fake_user_data.keys())
                }
             # 2. 构建包含上下文的用户输入
            context = (
                f"📊 用户档案：{req.ctx.user_id} | "
                f"孩子：{user_info['孩子姓名']} | "
                f"英语课时：{user_info['英语课时']}节 | "
                f"数学课时：{user_info['数学课时']}节"
            )
            
            # 将上下文和用户问题合并
            enhanced_user_input = f"""
            请根据以下用户档案信息回答问题：
            
            {context}
            
            用户问题：{req.ctx.user_input}
            """
            # 构建消息列表openai格式
            messages = [
                {"role": "user", "content": enhanced_user_input}
            ]


            add_log('INFO', f"收到用户【{req.ctx.user_id}】的请求：{req.ctx.user_input}")
            print(type(enhanced_user_input))
            # 3. 调用LLM
            response = await get_llm_client.call(messages)
            
            add_log('INFO', f"用户【{req.ctx.user_id}】的回复：{response}")
            
            # 4. 返回响应给客户端
            return {
                "code": 200,
                "msg": "success",
                "data": {
                    "response": response,
                    "user_info": {
                        "user_id": req.ctx.user_id,
                        "child_name": user_info['孩子姓名'],
                        "english_classes": user_info['英语课时'],
                        "math_classes": user_info['数学课时']
                    }
                }
            }
        except Exception as e:
            add_log('ERROR', f"处理用户【{req.ctx.user_id}】请求时出错：{str(e)}")
            return {
                "code": 500,
                "msg": f"处理请求时出错：{str(e)}"
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
    print("正在启动服务...")
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,#settings.WS_PORT,
        reload=True, # 开发环境开热重载，改代码自动重启
        log_level="info",#
         # 启动进程数
    )
