
from utils.logger import add_log
from core.graph.state import ChatState # 导入ChatState类型

# ❶ 入参类型从dict改成ChatState，IDE会自动补全所有字段
def generate_reply_node(state: ChatState) -> dict:
    # ❷ 把state["ctx"]改成state.ctx，属性访问更安全，写错字段立刻报错
    ctx = state.ctx
    # ✅ 正确用法：只调 add_log，传 ctx 参数
    # 效果：1. 控制台/文件会打印  2. ctx.logs 列表里会自动存入
    # 日志
    add_log("INFO", "进入回复生成节点", module="generate_reply_node", ctx=ctx)
    # 调用大模型
    reply = ctx.llm_client.call(
        messages=state.messages, 
        temperature=0.05,
        ctx=ctx
    )

    # 1. 从State里拿需要的参数，这里可以拿前置节点已经查好的课程数据（比如你后面加了查课节点的话）
    course_info = state.course_info
    if course_info:
        add_log("INFO", f"使用课程数据：{course_info}", module="generate_reply_node", ctx=ctx)

    # --------------------------
    # 修复3：只返回需要更新的字段增量，不要返回全量state
    return {
        # 保存生成的回复
        "generated_reply": reply,
        # 更新对话历史，把AI回复加进去，供多轮使用
        "messages": state.messages + [{"role": "assistant", "content": reply}]
    }