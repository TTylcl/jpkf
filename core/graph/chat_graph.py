

from langgraph.graph import StateGraph,END

from core.context import AgentContext
from .nodes.generate_node import generate_reply_node
from .state import ChatState


def build_chat_graph():
    workflow = StateGraph(ChatState)
    # 添加节点
    workflow.add_node("generate", generate_reply_node)
    # 设置入口点
    workflow.set_entry_point("generate")
    # 添加边
    workflow.add_edge("generate", END)
    # 编译
    return workflow.compile()







