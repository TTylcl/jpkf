"""
api/routers/debug_router.py
极简开发者调试面板 —— 一个文件搞定
功能：输入问题 → 查看 RAG 召回片段 / 相似度 / 来源 / 最终回答
"""
import json
import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from api.routers.auth_router import get_current_user
from schemas.chat_schemas import ChatRequest

ROLE_MAP = {
    "ADMIN": ("admin", "edu_admin_agent"),
    "STUDENT": ("student", "student_agent"),
    "TEACHER": ("teacher", "teacher_agent"),
    "PARENT": ("parent", "customer_service_agent"),
}

router = APIRouter(tags=["debug"])


def get_graph(request: Request):
    if not hasattr(request.app.state, "graph"):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Agent服务未初始化")
    return request.app.state.graph


# ══════════════════════════════════════════════════════════════
# 调试面板页面
# ══════════════════════════════════════════════════════════════

DEBUG_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent 调试面板</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; margin-bottom: 20px; font-size: 20px; }
  .container { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .panel { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
  .panel h2 { font-size: 14px; color: #8b949e; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  .full { grid-column: 1 / -1; }
  textarea, input { width: 100%; background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 10px; border-radius: 6px; font-size: 14px; font-family: inherit; resize: vertical; }
  textarea:focus, input:focus, select:focus { outline: none; border-color: #58a6ff; }
  select { background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 8px; border-radius: 6px; font-size: 13px; }
  .row { display: flex; gap: 10px; margin-bottom: 12px; align-items: center; }
  .row label { font-size: 13px; color: #8b949e; white-space: nowrap; }
  .row input { flex: 1; }
  button { background: #238636; color: #fff; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
  button:hover { background: #2ea043; }
  button:disabled { background: #30363d; cursor: not-allowed; }
  .chunk { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
  .chunk .meta { font-size: 12px; color: #8b949e; margin-bottom: 4px; display: flex; gap: 12px; }
  .chunk .meta .sim { color: #58a6ff; font-weight: 600; }
  .chunk .meta .src { color: #d2a8ff; }
  .chunk .text { font-size: 13px; line-height: 1.5; color: #c9d1d9; max-height: 120px; overflow-y: auto; }
  .answer-box { background: #0d1117; border: 1px solid #238636; border-radius: 6px; padding: 14px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; min-height: 60px; }
  .tools-list { font-size: 13px; }
  .tools-list .tool { padding: 6px 0; border-bottom: 1px solid #21262d; }
  .tools-list .tool-name { color: #7ee787; font-weight: 600; }
  .tools-list .tool-args { color: #8b949e; font-size: 12px; }
  .empty { color: #484f58; font-style: italic; font-size: 13px; }
  .stats { display: flex; gap: 16px; margin-bottom: 10px; }
  .stat { background: #0d1117; border-radius: 6px; padding: 8px 14px; }
  .stat .val { font-size: 18px; font-weight: 700; color: #58a6ff; }
  .stat .lbl { font-size: 11px; color: #8b949e; }
  .loading { color: #d29922; }
  .error { color: #f85149; }
  .intent-tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
  .intent-schedule { background: #1f3a5f; color: #58a6ff; }
  .intent-course { background: #2d1f3f; color: #d2a8ff; }
  .intent-general { background: #1f3520; color: #7ee787; }
</style>
</head>
<body>
<h1>🔬 Agent 调试面板</h1>

<div class="container">
  <!-- 输入区 -->
  <div class="panel full">
    <h2>📝 输入</h2>
    <div class="row">
      <label>用户名</label>
      <input id="username" value="admin001" placeholder="登录用户名">
      <label>密码</label>
      <input id="password" type="password" value="123456">
      <label>问题</label>
      <input id="question" value="钢琴课多少钱" placeholder="输入用户问题...">
      <button id="sendBtn" onclick="send()">发送</button>
    </div>
  </div>

  <!-- 意图 & 统计 -->
  <div class="panel">
    <h2>🎯 意图分类</h2>
    <div id="intentDisplay" class="empty">等待请求...</div>
    <div class="stats" id="stats" style="margin-top:12px"></div>
  </div>

  <!-- 工具调用 -->
  <div class="panel">
    <h2>🔧 工具调用链</h2>
    <div id="toolsDisplay" class="tools-list empty">等待请求...</div>
  </div>

  <!-- RAG 召回 -->
  <div class="panel full">
    <h2>📚 RAG 召回片段</h2>
    <div id="ragDisplay" class="empty">等待请求...</div>
  </div>

  <!-- 最终回答 -->
  <div class="panel full">
    <h2>💬 最终回答</h2>
    <div id="answerDisplay" class="answer-box empty">等待请求...</div>
  </div>
</div>

<script>
let current_thread_id = '';
let authToken = '';

async function login() {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error('登录失败: ' + t);
  }
  const data = await res.json();
  authToken = data.token;
  return authToken;
}

async function send() {

  const question = document.getElementById('question').value.trim();
  if (!question) return;

  const btn = document.getElementById('sendBtn');
  btn.disabled = true;
  btn.textContent = '请求中...';

  // 清空
  document.getElementById('ragDisplay').innerHTML = '<span class="loading">检索中...</span>';
  document.getElementById('answerDisplay').innerHTML = '<span class="loading">推理中...</span>';
  document.getElementById('toolsDisplay').innerHTML = '<span class="loading">执行中...</span>';
  document.getElementById('intentDisplay').innerHTML = '<span class="loading">分类中...</span>';
  document.getElementById('stats').innerHTML = '';

  try {
    if (!authToken) await login();
    const resp = await fetch('/api/debug/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + authToken,
      },
      body: JSON.stringify({ message: question, thread_id: current_thread_id }),
    });

    // HTTP 错误
    if (!resp.ok) {
      const text = await resp.text();
      document.getElementById('answerDisplay').innerHTML = '<span class="error">HTTP ' + resp.status + ': ' + escapeHtml(text.substring(0, 500)) + '</span>';
      document.getElementById('intentDisplay').innerHTML = '<span class="error">请求失败</span>';
      document.getElementById('ragDisplay').innerHTML = '<span class="empty">-</span>';
      document.getElementById('toolsDisplay').innerHTML = '<span class="empty">-</span>';
      return;
    }

    const data = await resp.json();
    current_thread_id = data.thread_id || '';

    // 错误处理
    if (data.error) {
      document.getElementById('answerDisplay').innerHTML = '<span class="error">' + escapeHtml(data.error) + '</span>';
      if (data.detail) document.getElementById('ragDisplay').innerHTML = '<pre style="font-size:11px;color:#f85149">' + escapeHtml(data.detail) + '</pre>';
      document.getElementById('intentDisplay').innerHTML = '<span class="error">请求失败</span>';
      document.getElementById('toolsDisplay').innerHTML = '<span class="empty">-</span>';
      return;
    }

    // 意图
    const intent = data.intent || 'general';
    const intentCls = intent === 'parent_schedule' ? 'intent-schedule'
                    : intent === 'parent_course' ? 'intent-course'
                    : 'intent-general';
    const intentNames = { parent_schedule: '排课查询', parent_course: '课程查询', general: '通用对话' };
    document.getElementById('intentDisplay').innerHTML =
      `<span class="intent-tag ${intentCls}">${intentNames[intent] || intent}</span>
       ${data.day_of_week ? ' | 星期: ' + data.day_of_week : ''}`;

    // 统计
    document.getElementById('stats').innerHTML =
      `<div class="stat"><div class="val">${data.rag_total_found || 0}</div><div class="lbl">RAG 召回</div></div>
       <div class="stat"><div class="val">${data.rag_total_used || 0}</div><div class="lbl">RAG 采用</div></div>
       <div class="stat"><div class="val">${data.tool_count || 0}</div><div class="lbl">工具调用</div></div>`;

    // 工具调用链
    if (data.tool_calls && data.tool_calls.length > 0) {
      document.getElementById('toolsDisplay').innerHTML = data.tool_calls.map(t =>
        `<div class="tool">
          <span class="tool-name">${t.name}</span>
          <span class="tool-args">(${t.args || ''})</span>
          ${t.error ? '<span class="error">❌ ' + t.error + '</span>' : '✅'}
        </div>`
      ).join('');
    } else {
      document.getElementById('toolsDisplay').innerHTML = '<span class="empty">无工具调用</span>';
    }

    // RAG 召回
    if (data.rag_chunks && data.rag_chunks.length > 0) {
      document.getElementById('ragDisplay').innerHTML = data.rag_chunks.map((c, i) =>
        `<div class="chunk">
          <div class="meta">
            <span>#${i + 1}</span>
            <span class="sim">相似度: ${(c.similarity * 100).toFixed(1)}%</span>
            <span class="src">来源: ${c.source}</span>
            <span>chunk #${c.chunk_index}</span>
          </div>
          <div class="text">${escapeHtml(c.chunk_text)}</div>
        </div>`
      ).join('');
    } else {
      document.getElementById('ragDisplay').innerHTML = '<span class="empty">本次请求未触发 RAG 检索</span>';
    }

    // 最终回答
    document.getElementById('answerDisplay').textContent = data.final_answer || '(无回答)';

  } catch (e) {
    document.getElementById('answerDisplay').innerHTML = '<span class="error">请求失败: ' + e.message + '</span>';
  } finally {
    btn.disabled = false;
    btn.textContent = '发送';
  }
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// 回车发送
document.getElementById('question').addEventListener('keydown', e => {
  if (e.key === 'Enter') send();
});
</script>
</body>
</html>"""


@router.get("/debug", response_class=HTMLResponse)
async def debug_panel():
    """开发者调试面板"""
    return HTMLResponse(content=DEBUG_HTML)


# ══════════════════════════════════════════════════════════════
# 调试 Chat 接口 —— 返回完整 trace
# ══════════════════════════════════════════════════════════════

@router.post("/debug/chat")
async def debug_chat(req: ChatRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """
    调试用 Chat 接口：返回 RAG 召回片段、相似度、来源、最终回答等完整 trace。
    身份来自 token（由 get_current_user 校验），不再信任请求体里的 user_id。
    """
    graph = get_graph(request)

    # 1. 身份来自 token（修复 IDOR：不接受客户端传 user_id 冒充他人）
    user_id = current_user["user_id"]
    mapping = ROLE_MAP.get(current_user["user_type"])
    if not mapping:
        return {"error": f"未知用户类型: {current_user['user_type']}"}
    role, agent_role = mapping

    # 2. 构建 config
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "user_role": role,
            "agent_role": agent_role,
            "trace_id": str(uuid.uuid4()),
        }
    }

    # 3. 调 graph —— 用 ainvoke（与正常 chat 一致）
    try:
        final_state = await graph.ainvoke(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Agent调用失败: {str(e)}", "detail": traceback.format_exc()}

    if final_state is None:
        return {"error": "Agent未返回任何状态"}

    # 4. 解析 state
    messages = final_state.get("messages", [])
    intent = final_state.get("intent", "general")
    day_of_week = final_state.get("day_of_week")

    # 提取 RAG 结果
    rag_chunks = []
    rag_total_found = 0
    rag_total_used = 0

    tool_calls = []
    last_tool_name = None
    last_tool_args = ""

    for msg in messages:
        # AIMessage → 工具调用请求（先出现）
        if isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    last_tool_name = tc.get("name", "")
                    last_tool_args = json.dumps(tc.get("args", {}), ensure_ascii=False)
                    tool_calls.append({
                        "name": tc.get("name", "unknown"),
                        "args": last_tool_args,
                        "error": None,
                    })

        # ToolMessage → 工具结果
        if isinstance(msg, ToolMessage):
            name = getattr(msg, "name", "unknown")
            content = getattr(msg, "content", "")

            # 去重：只在 AIMessage 没记录过时补一条
            already_recorded = any(tc["name"] == name for tc in tool_calls)
            if not already_recorded:
                tool_calls.append({
                    "name": name,
                    "args": last_tool_args,
                    "error": None,
                })

            # 解析 RAG 返回
            if name == "rag_search" and content:
                try:
                    parsed = json.loads(content) if isinstance(content, str) else content
                    if isinstance(parsed, dict):
                        data = parsed.get("data", {})
                        if isinstance(data, dict):
                            docs = data.get("documents", [])
                            rag_total_found = data.get("total_found", len(docs))
                            rag_total_used = data.get("total_used", len(docs))
                            for doc in docs:
                                distance = doc.get("distance", 1.0)
                                similarity = max(0.0, min(1.0, 1.0 - float(distance)))
                                rag_chunks.append({
                                    "chunk_text": doc.get("chunk_text", ""),
                                    "source": doc.get("source", ""),
                                    "chunk_index": doc.get("chunk_index", 0),
                                    "distance": float(distance),
                                    "similarity": round(similarity, 4),
                                })
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

    # 按相似度降序排列 RAG 结果
    rag_chunks.sort(key=lambda x: x["similarity"], reverse=True)

    # 提取最终回答（跳过反思确认短句）
    final_answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not (hasattr(msg, "tool_calls") and msg.tool_calls):
            content = msg.content
            text = content if isinstance(content, str) else str(content)
            stripped = text.strip()
            if stripped in ('。', '完整', 'OK', 'ok', '已完整', '.', '✅'):
                continue
            final_answer = text
            break

    # 去重 tool_calls（同名合并）
    seen = set()
    unique_tools = []
    for t in tool_calls:
        key = t["name"]
        if key not in seen:
            seen.add(key)
            unique_tools.append(t)

    return {
        "question": req.message,
        "intent": intent,
        "day_of_week": day_of_week,
        "rag_chunks": rag_chunks,
        "rag_total_found": rag_total_found,
        "rag_total_used": rag_total_used,
        "tool_calls": unique_tools,
        "tool_count": len(unique_tools),
        "final_answer": final_answer,
        "thread_id": thread_id,
    }