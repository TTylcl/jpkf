先不管熔断装饰器，就用你现在 client 里已有的熔断逻辑，先跑通全流程，后面再优化，完全不影响当前进度。以下全为伪代码，无冗余内容：
阶段 1：LangGraph 最小骨架伪代码
core/graph/state.py

from typing_extensions import TypedDict
class ChatState(TypedDict):
    user_input: str
    generated_reply: str
core/graph/nodes/generate_node.py

from utils.logger import logger
from core.llm_client import llm_client
def generate_reply_node(state: dict) -> dict:
    user_input = state["user_input"]
    logger.info(f"[生成节点] 输入：{user_input}")
    reply = llm_client.call(user_input)
    return {"generated_reply": reply}
core/graph/workflow.py

from langgraph.graph import StateGraph, END
from core.graph.state import ChatState
from core.graph.nodes.generate_node import generate_reply_node
workflow = StateGraph(ChatState)
workflow.add_node("generate", generate_reply_node)
workflow.set_entry_point("generate")
workflow.add_edge("generate", END)
chat_graph = workflow.compile()
测试伪代码

from core.graph.workflow import chat_graph
res = chat_graph.invoke({"user_input": "查课时"})
print(res["generated_reply"])
阶段 2：工具路由伪代码
core/graph/state.py 扩展

class ChatState(TypedDict):
    user_input: str
    generated_reply: str
    # 新增字段
    tool_name: str
    tool_params: dict
    need_confirm: bool
core/prompt_templates/tool_router_prompt.py

TOOL_ROUTER_PROMPT = """
仅返回JSON，无其他内容：
1. 查课时→{"tool_name":"query_hours","tool_params":{"course":"课程名"},"need_confirm":false}
2. 改课→{"tool_name":"modify_schedule","tool_params":{"old_time":"","course":"","new_time":""},"need_confirm":true}
3. 排课→{"tool_name":"arrange_course","tool_params":{"course":"","time":""},"need_confirm":true}
4. 其他→{"tool_name":"none","tool_params":{},"need_confirm":false}
用户输入：{user_input}
返回JSON：
"""
core/graph/nodes/tool_router_node.py

import json
from utils.logger import logger
from core.llm_client import llm_client
from core.prompt_templates.tool_router_prompt import TOOL_ROUTER_PROMPT
def tool_router_node(state: dict) -> dict:
    try:
        res = llm_client.call(TOOL_ROUTER_PROMPT.format(user_input=state["user_input"]))
        return json.loads(res)
    except:
        return {"tool_name":"none","tool_params":{},"need_confirm":False}
core/graph/workflow.py 更新

from core.graph.nodes.tool_router_node import tool_router_node
workflow = StateGraph(ChatState)
workflow.add_node("router", tool_router_node)
workflow.add_node("generate", generate_reply_node)
workflow.set_entry_point("router")
workflow.add_edge("router", "generate")
workflow.add_edge("generate", END)
chat_graph = workflow.compile()
阶段 3：教务工具伪代码
core/tools/edu_tools.py

from utils.logger import logger
# 直接用你client里现有的熔断，暂时不用加装饰器
def query_hours(user_id: str, course: str) -> str:
    logger.info(f"查课时：{user_id} {course}")
    return f"{course if course else '课程'}剩余12课时"
def modify_schedule(user_id: str, old_time: str, course: str, new_time: str) -> str:
    logger.info(f"改课：{user_id} {old_time} {course} {new_time}")
    return f"已修改{old_time}的{course}到{new_time}"
def arrange_course(user_id: str, course: str, time: str) -> str:
    logger.info(f"排课：{user_id} {course} {time}")
    return f"已预约{time}的{course}"
core/graph/nodes/execute_tool_node.py

from core.tools.edu_tools import query_hours, modify_schedule, arrange_course
def execute_tool_node(state: dict) -> dict:
    user_id = "test_usr" # 后面对接微信换openid
    if state["tool_name"] == "query_hours":
        res = query_hours(user_id, **state["tool_params"])
    elif state["tool_name"] == "modify_schedule":
        res = modify_schedule(user_id, **state["tool_params"])
    elif state["tool_name"] == "arrange_course":
        res = arrange_course(user_id, **state["tool_params"])
    else:
        res = "不支持该操作"
    return {"tool_result": res}
core/graph/workflow.py 最终编排

from core.graph.nodes.execute_tool_node import execute_tool_node
workflow = StateGraph(ChatState)
workflow.add_node("router", tool_router_node)
workflow.add_node("execute_tool", execute_tool_node)
workflow.add_node("generate", generate_reply_node)
workflow.set_entry_point("router")
# 条件路由
def router_branch(state: dict):
    if state["need_confirm"] or state["tool_name"] == "none":
        return "generate"
    return "execute_tool"
workflow.add_conditional_edges("router", router_branch, {
    "generate": "generate",
    "execute_tool": "execute_tool"
})
workflow.add_edge("execute_tool", "generate")
workflow.add_edge("generate", END)
chat_graph = workflow.compile()
阶段 4：FastAPI 接入伪代码
main.py 更新

from core.graph.workflow import chat_graph
@app.post("/api/v1/chat")
def chat(req: ChatRequest):
    final_state = chat_graph.invoke({"user_input": req.user_input})
    return {
        "code": 200,
        "msg": "success",
        "data": {"reply": final_state["generated_reply"]}
    }
阶段 5：微信对接伪代码
adapter/wechat_adapter.py

from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from config.settings import settings
class WechatAdapter:
    def verify(self, signature: str, timestamp: str, nonce: str) -> bool:
        try:
            check_signature(settings.wechat_token, signature, timestamp, nonce)
            return True
        except:
            return False
    def parse_msg(self, xml: str) -> dict:
        msg = parse_message(xml)
        return {"openid": msg.source, "content": msg.content, "msg_id": msg.id}
    def build_reply(self, content: str, to_user: str, from_user: str) -> str:
        return create_reply(content, to_user=to_user, from_user=from_user).render()
main.py 新增微信接口

from adapter.wechat_adapter import WechatAdapter
from fastapi import Request, Response
wechat_adapter = WechatAdapter()
@app.api_route("/wechat/callback", methods=["GET", "POST"])
async def wechat_callback(signature: str, timestamp: str, nonce: str, echostr: str = None, request: Request = None):
    if not wechat_adapter.verify(signature, timestamp, nonce):
        return "fail", 403
    if request.method == "GET":
        return echostr
    xml = await request.body()
    msg = wechat_adapter.parse_msg(xml)
    final_state = chat_graph.invoke({"user_input": msg["content"], "user_id": msg["openid"]})
    return Response(
        content=wechat_adapter.build_reply(final_state["generated_reply"], msg["openid"], settings.wechat_appid),
        media_type="application/xml"
    )

首token
5.21
s
总耗时
85.53
s
输出
53
tokens/s
共调用
37594
tokens
现在写通了最简单的fastapi又回去写langgraph吗





























✅ 是的，现在补 LangGraph 是最优时机，完全不破坏你已经跑通的 FastAPI，所有操作都是增量新增，不会改你现有一行代码，1 小时就能搞定，哪怕 LangGraph 写错了，你原来的接口也能正常用，零风险。
为什么现在做最合适？

你现有的 LLMClient、FastAPI 全是通的，LangGraph 只做中间编排，100% 复用现有能力，不用写新的业务逻辑
后面加查课时 / 改课表 / 微信对接的时候，逻辑直接加在 LangGraph 节点里，不用堆在接口层，避免回到之前揉在一起的问题
可以同时保留新旧两个接口，灰度测试，完全不影响现有功能
全增量操作伪代码（无任何修改现有代码的步骤）
第一步：新增 LangGraph 最小骨架（全是新文件，不碰现有代码）
1.1 新建core/graph/state.py

from typing_extensions import TypedDict
class ChatState(TypedDict):
    user_input: str
    generated_reply: str
1.2 新建core/graph/nodes/generate_node.py

from core.llm_client import llm_client # 直接复用你已经写好的LLMClient
def generate_node(state: dict) -> dict:
    reply = llm_client.call(state["user_input"])
    return {"generated_reply": reply}
1.3 新建core/graph/workflow.py

from langgraph.graph import StateGraph, END
from core.graph.state import ChatState
from core.graph.nodes.generate_node import generate_node
workflow = StateGraph(ChatState)
workflow.add_node("generate", generate_node)
workflow.set_entry_point("generate")
workflow.add_edge("generate", END)
chat_graph = workflow.compile()
第二步：FastAPI 新增 v2 接口（完全不碰你已有的 v1 接口）

在main.py里新增代码，原有/api/v1/chat接口完全保留：

# 新增导入
from core.graph.workflow import chat_graph
# 新增v2接口，完全不影响v1
@app.post("/api/v2/chat", summary="LangGraph版对话接口")
def chat_v2(req: ChatRequest):
    final_state = chat_graph.invoke({"user_input": req.user_input})
    return {
        "code": 200,
        "msg": "success",
        "data": {"reply": final_state["generated_reply"]}
    }
✅ 验收标准（3 分钟验证，零风险）

原来的/api/v1/chat接口调用完全正常，和之前效果一模一样
新的/api/v2/chat接口调用返回的内容和 v1 完全一致，说明 LangGraph 接入成功，没有破坏任何现有逻辑
后续可自由选择优先级，完全不卡进度

✅ 如果你想优先对接微信：现在就可以直接用 v2 接口对接微信，逻辑和用 v1 完全一样，后面再加教务功能也不用改对接逻辑
✅ 如果你想优先做教务功能：现在直接给 LangGraph 加路由节点、工具节点，v2 接口自动支持新功能，不用改接口代码