
#api/routers/ai_chat_router.py

import uuid
from fastapi import APIRouter, Request, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable

#流式接口
import json
from fastapi.responses import StreamingResponse
"""
导入说明：
    APIRouter,      # ✅ 路由分组管理 - 将相关端点组织在一起
    Request,        # ✅ 原始HTTP请求 - 获取请求头、客户端IP等
    HTTPException,  # ✅ 标准错误响应 - 抛出4xx/5xx错误

"""
from schemas.chat_schemas import ChatRequest, ChatResponse

from core.database import AsyncDatabase
from dal.dao.user_dao import UserDao
from utils.logger import add_log
ROLE_MAP = {
    "ADMIN": ("admin", "edu_admin_agent"),
    "STUDENT": ("student", "student_agent"),
    "TEACHER": ("teacher", "teacher_agent"),
    "PARENT": ("parent", "customer_service_agent"),
}

router = APIRouter(tags=['ai对话'])




#graph依赖注入
def get_graph(request: Request)->Runnable:
    """从 app.state 拿编译好的 graph（依赖注入）"""
    if not hasattr(request.app.state, 'graph'):
        raise HTTPException(status_code=503, detail='Agent服务未初始化')
    return request.app.state.graph


#对话接口
@router.post('/chat',response_model=ChatResponse)
async def chat(req:ChatRequest,request:Request):
    """
    对话接口
    参数说明：
        req: ChatRequest - 对话请求体
        request: Request - 原始HTTP请求
        返回： ChatResponse - 对话结果

    """
    #获取图谱
    graph = get_graph(request)
 

    #1 构建上下文
    async with AsyncDatabase.get_session() as session:
        user_dao = UserDao(session)
        user = await user_dao.get_by_id(int(req.user_id))
        if not user:
            return ChatResponse(code=400, message=f"用户不存在: {req.user_id}", reply="", thread_id='')
        raw_role = user.user_type
        mapping = ROLE_MAP.get(raw_role)
        if not mapping:
            return ChatResponse(code=400, message=f"未知用户类型: {raw_role}", reply="", thread_id='')
        role, agent_role = mapping
    #2 会话管理 + 加载历史（先加载，不包含当前消息）
    async with AsyncDatabase.get_session() as session:
        from service.conversation_service import ConversationService
        conv_svc = ConversationService(session)
        session_info = await conv_svc.get_or_create_session(
            user_id=int(req.user_id),
            thread_id=req.thread_id
        )
        history_messages = await conv_svc.get_history_messages(session_info.session_id, limit=20)
        thread_id = session_info.thread_id
        session_id = session_info.session_id

    #3 构建 config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": req.user_id,
            "user_role": role,
            "agent_role": agent_role,
            "trace_id": str(uuid.uuid4()),
        }
    }

    #4 调用 graph
    try:
        add_log("INFO", f"history_messages: {len(history_messages)} 条", module="ai_chat")
        result = await graph.ainvoke(
            {'messages': history_messages + [HumanMessage(content=req.message)]},
            config=config,
        )
    except Exception as e:
        return ChatResponse(code=500, message=f"Agent调用失败: {str(e)}", reply="", thread_id=thread_id)

    #5 提取 AI 回复
    reply = ''
    for msg in reversed(result.get('messages', [])):
        if isinstance(msg, AIMessage):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                continue
            content = msg.content
            text = content if isinstance(content, str) else str(content)
            stripped = text.strip()
            if stripped in ('。', '完整', 'OK', 'ok', '已完整', '.', '✅'):
                continue
            reply = text
            break
    if not reply:
        return ChatResponse(code=500, message="Agent未返回有效内容", reply="", thread_id=thread_id)

    #6 保存用户消息 + AI 回复
    async with AsyncDatabase.get_session() as db_session:
        from service.conversation_service import ConversationService
        conv_svc = ConversationService(db_session)
        await conv_svc.save_user_message(session_id, req.message, int(req.user_id))
        intent = result.get("intent", "")
        await conv_svc.save_ai_message(session_id, reply, intent=intent)
        add_log("INFO", f"消息已持久化 session_id={session_id} intent={intent}", module="ai_chat")

    return ChatResponse(code=200, message="success", reply=reply, thread_id=thread_id)
@router.post('/chat_stream')
async def chat_stream(req:ChatRequest,request:Request):
    """
    流式对话接口（SSE）
        每生成一个 token 就推送给前端，像 ChatGPT 那样逐字输出
    参数说明：
        req: ChatRequest - 对话请求体
        request: Request - 原始HTTP请求
        返回： StreamingResponse - 流式响应
    """
    graph = get_graph(request)
    #1用户身份-确定角色
    async with AsyncDatabase.get_session() as session:
        user_dao = UserDao(session)
        user = await user_dao.get_by_id(int(req.user_id))
        if not user:
            raise HTTPException(status_code=400, detail=f"用户不存在: {req.user_id}")
        raw_role = user.user_type
        mapping = ROLE_MAP.get(raw_role)
        if not mapping:
            raise HTTPException(status_code=400, detail=f"未知用户类型: {raw_role}")
        role, agent_role = mapping
    #2 会话管理 + 加载历史（先加载，不包含当前消息）
    async with AsyncDatabase.get_session() as session:
        from service.conversation_service import ConversationService
        conv_svc = ConversationService(session)
        session_info = await conv_svc.get_or_create_session(
            user_id=int(req.user_id),
            thread_id=req.thread_id
        )
        history_messages = await conv_svc.get_history_messages(session_info.session_id, limit=20)
        session_id = session_info.session_id
        thread_id = session_info.thread_id
        add_log("INFO", f"[stream] history_messages: {len(history_messages)} 条", module="ai_chat")

    #构建config
    trace_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": req.user_id,
            "user_role": role,
            "agent_role": agent_role,
            "trace_id": trace_id,
        }
    }
    #流式生成
    async def event_generator():
        full_reply = ''
        try:
            async for event in graph.astream_events(
                {'messages': history_messages + [HumanMessage(content=req.message)]},
                config=config,
                version="v2",   #
            ):
                kind = event['event']
                # --- LLM 逐 token 输出 ---
                if kind == "on_chat_model_stream":
                      chunk = event["data"]["chunk"]
                      if chunk.content:
                          full_reply += chunk.content
                          yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                # --- 工具调用开始 ---
                elif kind == "on_tool_start":
                      tool_name = event.get("name", "unknown")
                      tool_input = event["data"].get("input", {})
                      yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'input': str(tool_input)[:200]}, ensure_ascii=False)}\n\n"
                # --- 工具调用结束 ---
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event["data"].get("output", "")
                    output_preview = str(output)[:200]
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'output': output_preview}, ensure_ascii=False)}\n\n"
            # --- 保存用户消息 + AI 回复 ---
            async with AsyncDatabase.get_session() as db_session:
                from service.conversation_service import ConversationService
                c_svc = ConversationService(db_session)
                await c_svc.save_user_message(session_id, req.message, int(req.user_id))
                if full_reply:
                    await c_svc.save_ai_message(session_id, full_reply)
                    add_log("INFO", f"[stream] 消息已持久化 session_id={session_id}", module="ai_chat")
            # --- 结束 ---
            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id, 'trace_id': trace_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )












