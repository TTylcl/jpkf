"""
意图分类节点（Agent Router 的决策中枢）

职责：读用户消息 → LLM 结构化分类 → 输出 intent + day_of_week。

准确率策略（四维度，分两期）：    ✅ 维度 1：对话历史压缩注入 —— 消除指代歧义（"那明天呢"）
✅ 维度 2：用户画像注入 —— 消除身份歧义（parent vs student）
📋 维度 3：边界样本 + 思维链 —— 后续扩展，需切换为自由输出 + 正则提取
📋 维度 4：置信度 + 降级 —— 后续扩展，需先积累真实分类日志确定阈值

设计原则：
1. 纯 LLM 分类，零关键词匹配 —— 语义理解交给语言模型
2. 上下文注入而非猜测 —— LLM 不知道的信息（时间/身份）显式传入
3. 角色短路 —— 非 parent 不调 LLM，直接 general
4. 静默降级 —— LLM 失败时走 general，不中断请求
"""

from __future__ import annotations

from datetime import datetime

from langchain_core.messages import (
    HumanMessage, SystemMessage, AIMessage, ToolMessage
)
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field
from typing import Literal

from agent.state import AgentState
from core.context import AgentContext
from core.prompt_templates.base_templates import INTENT_CLASSIFIER_PROMPT
# ══════════════════════════════════════════════════════════════════════
# 结构化输出
# ══════════════════════════════════════════════════════════════════════
class IntentResult(BaseModel):
    """
    LLM 意图分类的结构化输出。

    用 with_structured_output 强制 LLM 按此 schema 输出，
    杜绝自由文本解析的歧义。

    注：维度 3（思维链）启用时，这里改为自由文本 + 正则提取方案。
    """
    intent: Literal["parent_schedule", "parent_course", "general"] = Field(
        description="意图分类：parent_schedule=排课查询（有时间锚点），"
                    "parent_course=课程查询（无时间锚点，问内容），"
                    "general=通用对话（其他一切）"
    )
    day_of_week: int | None = Field(
        default=None,
        description="用户关心的星期几：1=周一..7=周日。"
                    "用户说了具体星期X才填数字。"
                    "'今天/明天/后天'不转换，填 null。"
                    "无法判断填 null。"
    )
# ══════════════════════════════════════════════════════════════════════
# 维度 1：对话历史压缩注入
# ══════════════════════════════════════════════════════════════════════

# 最多取最近几轮对话
_MAX_HISTORY_ROUNDS = 3
# 历史文本字符上限
_MAX_HISTORY_CHARS = 500

def _compress_history(messages: list):
    """
    从消息历史中提取最近几轮对话，作为分类上下文。

    策略：
    - 倒序遍历，取最近不超过 _MAX_HISTORY_ROUNDS 轮
    - HumanMessage → 保留原文
    - AIMessage → 保留文本部分（无 content 的纯 tool_call 跳过）
    - ToolMessage → 丢弃 —— 工具返回的 JSON 数据对分类无意义
    - 总字符数超 _MAX_HISTORY_CHARS 时从旧到新截断

    Returns:
        格式化的对话历史字符串。无历史时返回空字符串。
    """
    # 无消息或单轮对话时返回空字符串
    if not messages or len(messages) <= 1:
        return ""
    # 倒序遍历
    rounds: list[str] = []
    char_count = 0
    round_count = 0 # 轮数计数
    # 排除最后一条（那是当前消息，不是历史）
    history = messages[:-1]

    for msg in reversed(history):
        if isinstance(msg,HumanMessage): #如果是HumanMessage
            content = _safe_content(msg)  # 获取消息内容
            prefix = "用户："
        elif isinstance(msg,AIMessage):   #如果是AIMessage
            content = _safe_content(msg) 
            if not content:  # 纯 tool_call 跳过
                continue
            prefix = "AI："
        elif isinstance(msg,ToolMessage):  # 如果是ToolMessage
            # 工具返回的 JSON 数据对分类无意义
            continue
        else:  # 其他消息类型跳过
            continue
        line = prefix + content # 生成一行对话
        if char_count + len(line) > _MAX_HISTORY_CHARS:
            # 超出字符数时截断
            break
        rounds.insert(0, line) # 插入到列表开头
        char_count += len(line)  # 更新字符数
        # 只数 HumanMessage，一轮对话 = 一条用户消息
        if isinstance(msg, HumanMessage):
            round_count += 1
            if round_count >= _MAX_HISTORY_ROUNDS:
                break
    if not rounds:  # 无对话时返回空字符串
        return ""
    return "【对话历史】\n" + "\n".join(rounds) + "\n\n"

def _safe_content(msg) -> str:
      """安全提取消息文本内容。"""
      content = getattr(msg, "content", "") # 尝试获取 content
      if isinstance(content, str): # 如果是字符串则返回
          return content
      if isinstance(content, list): # 如果是列表则尝试解析
          # content 可能是 [{"type": "text", "text": "..."}, ...]
          parts = []
          for block in content:
              if isinstance(block, dict) and block.get("type") == "text":
                  parts.append(block.get("text", ""))
          return "".join(parts)
      return str(content)

# ══════════════════════════════════════════════════════════════════════
# 维度 2：用户画像注入
# ══════════════════════════════════════════════════════════════════════
def _build_user_profile(state: AgentState, user_role: str) -> str:
    """
    从 state 构造用户画像文本，消除身份歧义。

    只读 state 已有字段，不触发数据库查询。
    children_data 不存在时标注"未获取"。
    """
    parts = [f"- 用户角色：{user_role}"]

    if user_role == "parent":
        children = state.get("children_data")
        if children and isinstance(children, list) and len(children) > 0:
            child_names = []
            for c in children:
                name = c.get("student_name", "")
                sid = c.get("student_id", "")
                if name:
                    child_names.append(name)
                elif sid:
                    child_names.append(f"学生ID:{sid}")
            if child_names:
                parts.append(f"- 关联孩子：{', '.join(child_names)}")
            else:
                parts.append("- 关联孩子：未获取（首次请求时尚未查询）")
        else:
            parts.append("- 关联孩子：未获取（首次请求时尚未查询）")

    return "【用户画像】\n" + "\n".join(parts) + "\n\n"

# ══════════════════════════════════════════════════════════════════════
# 时间上下文
# ══════════════════════════════════════════════════════════════════════

def _build_time_context() -> str:
    """
    构造时间上下文。

    LLM 训练数据有时效盲区，不知道"现在是什么时候"。
    把当前日期和星期显式注入，LLM 可以准确解析"今天/明天/后天/周三"。
    """
    now = datetime.now()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    today_dow = now.isoweekday()  # 
    #计算明天。后天的day_of_week 循环
    tomorrow_dow = today_dow + 1 if today_dow < 7 else 1
    after_tomorrow_dow = today_dow + 2 if today_dow <6 else (today_dow+2)%7 or 7
    return (
        f"【时间上下文】\n"
        f"- 当前日期：{now.strftime('%Y年%m月%d日')} {weekday_names[today_dow - 1]}\n"
        f"- 今天 = 星期{today_dow}（{weekday_names[today_dow - 1]}）\n"
        f"- 明天 = 星期{tomorrow_dow}（{weekday_names[tomorrow_dow - 1]}）\n"
        f"- 后天 = 星期{after_tomorrow_dow}（{weekday_names[after_tomorrow_dow - 1]}）\n"
        f"- day_of_week 编码：1=周一..7=周日\n\n"
    )

# ══════════════════════════════════════════════════════════════════════
# LLM 分类器（单例缓存）
# ══════════════════════════════════════

_classifier_llm = None

def _get_classifier_llm():
    """
    获取分类专用 LLM。

    与对话 LLM 分开配置：
    - temperature=0（分类要确定性，不要创造性）
    - 不绑工具（分类不需要调工具）
    - 模块级缓存（避免每次请求重建）
    """
    global _classifier_llm
    if _classifier_llm is None:
        from agent.llm import create_chat_model
        _classifier_llm = create_chat_model(temperature=0)
    return _classifier_llm

# ══════════════════════════════════════════════════════════════════════
# 节点入口
# ══════════════════════════════════════════════════════════════════════
async def classify_intent_node(
      state: AgentState,
      config: RunnableConfig,
      runtime: Runtime[AgentContext],
  ) -> dict:
    """
    意图分类节点 —— Agent Router 的决策中枢。

    完整流程：
    1. 取用户最后一条消息
    2. 确定 user_role（优先 Runtime，兜底 state）
    3. 非 parent → 直接 general（业务短路，省一次 LLM 调用）
3.5 已有 intent 且非 general → 直接复用（多轮对话意图复用，省 LLM 调用）
    4. parent → 组装上下文 + LLM 结构化分类
            上下文包含：
            - INTENT_CLASSIFIER_PROMPT（固定分类规则）
            - 时间上下文（维度 2 辅助）
            - 用户画像（维度 2）
            - 对话历史（维度 1）
            - 当前消息
    5. LLM 调用失败 → 静默降级 general

    Args:
        state: 当前 AgentState
        config: LangGraph RunnableConfig
        runtime: LangGraph Runtime[AgentContext]

    Returns:
        dict: {"intent": str, "day_of_week": int | None}
    """
    messages = state["messages"]
    if not messages:
        return {"intent": "general", "day_of_week": None}
    # ── 1. 取用户最后一条消息 ──
    last_msg = messages[-1]
    user_input = (
        last_msg.content if hasattr(last_msg, "content")
        else str(last_msg)
    )

    # ── 2. 确定 user_role ──
    #    优先级：Runtime.context > config.configurable > state（兜底）
    ctx = runtime.context
    if ctx is not None and ctx.user_role:
        user_role = ctx.user_role
    else:
        cfg = config.get("configurable", {})
        user_role = cfg.get("user_role") or state.get("user_role", "")

    # ── 3. 非 parent 短路 ──
    if user_role != "parent":
        return {"intent": "general", "day_of_week": None}

    # ── 3.5 意图复用（P2）：已有 intent 且非 general → 跳过 LLM 分类 ──
    existing_intent = state.get("intent")
    if existing_intent and existing_intent != "general":
        # 上一轮已经分好了（parent_schedule / parent_course），
        # 后续轮次无需重复分类，直接复用
        # ✅ 防御性处理：如果 checkpoint 反序列化出 IntentResult 对象，提取 .intent
        if isinstance(existing_intent, IntentResult):
            _intent = existing_intent.intent
            _dow = existing_intent.day_of_week
        else:
            _intent = str(existing_intent)
            _dow = state.get("day_of_week")
        return {"intent": _intent, "day_of_week": _dow}

    # ── 4. parent 组装上下文 ──
    history = _compress_history(messages)
    profile =  _build_user_profile(state,user_role)
    time = _build_time_context()

    system_message = (
        INTENT_CLASSIFIER_PROMPT + "\n\n"
        + time
        + profile

    )
    human_message = history + "[当前消息]\n" + user_input

    # ── 5. LLM 调用 ──
    try:
        llm = _get_classifier_llm()
        structured_llm = llm.with_structured_output(IntentResult)
        result: IntentResult = await structured_llm.ainvoke([
            SystemMessage(content=system_message),
            HumanMessage(content=human_message),
        ])
        # ✅ 显式提取纯 Python 值后丢弃 IntentResult 对象，
        #    防止 Pydantic 序列化 checkpoint 时泄露
        _intent: str = str(result.intent)
        _dow: int | None = result.day_of_week
        del result
        return {"intent": _intent, "day_of_week": _dow}
    except Exception as e:
        # LLM 调用失败 → 静默降级为 general
        # 通用 ReAct 子图仍能处理请求，只是路径不是最优
        return {"intent": "general", "day_of_week": None}


__all__ = ["classify_intent_node", "IntentResult"]

