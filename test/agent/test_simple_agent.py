from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
import operator

# ========== 1. 定义状态 ==========
class State(TypedDict):
    # 用户输入
    user_input: str
    # AI回复
    ai_response: str
    # 对话历史
    conversation: List[str]

# ========== 2. 创建节点函数 ==========
def receive_input(state: State):
    """接收用户输入"""
    # 模拟用户输入
    user_message = "你好，我想了解LangGraph"
    print(f"📥 用户输入: {user_message}")
    
    # 添加到对话历史
    conversation = state.get("conversation", [])
    conversation.append(f"用户: {user_message}")
    
    return {
        "user_input": user_message,
        "conversation": conversation
    }

def process_query(state: State):
    """处理查询"""
    user_input = state["user_input"]
    
    # 简单的处理逻辑
    if "LangGraph" in user_input:
        response = "LangGraph是用于构建多步骤AI工作流的库"
    elif "你好" in user_input:
        response = "你好！我是AI助手"
    else:
        response = f"我收到了你的消息: {user_input}"
    
    print(f"🤖 AI处理: {response}")
    
    return {"ai_response": response}

def format_response(state: State):
    """格式化响应"""
    response = state["ai_response"]
    
    # 添加到对话历史
    conversation = state["conversation"]
    conversation.append(f"AI: {response}")
    
    # 格式化输出
    formatted = f"✨ AI回复: {response}"
    print(formatted)
    
    return {
        "conversation": conversation,
        "ai_response": formatted
    }

# ========== 3. 构建工作流 ==========
def build_workflow():
    """构建简单工作流"""
    # 创建图
    workflow = StateGraph(State)
    
    # 添加节点
    workflow.add_node("接收输入", receive_input)
    workflow.add_node("处理查询", process_query)
    workflow.add_node("格式化回复", format_response)
    
    # 设置入口点
    workflow.set_entry_point("接收输入")
    
    # 连接节点
    workflow.add_edge("接收输入", "处理查询")
    workflow.add_edge("处理查询", "格式化回复")
    workflow.add_edge("格式化回复", END)
    
    # 编译工作流
    app = workflow.compile()
    
    return app

# ========== 4. 运行工作流 ==========
if __name__ == "__main__":
    print("🚀 启动LangGraph工作流...")
    
    # 构建工作流
    app = build_workflow()
    
    print("\n" + "="*50)
    print("📊 工作流结构:")
    print("接收输入 → 处理查询 → 格式化回复 → 结束")
    print("="*50 + "\n")
    
    # 初始状态
    initial_state = {
        "user_input": "",
        "ai_response": "",
        "conversation": []
    }
    
    # 执行工作流
    print("🔄 开始执行...")
    result = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("✅ 执行完成!")
    print("="*50)
    
    # 显示最终结果
    print("\n📝 对话历史:")
    for i, message in enumerate(result["conversation"], 1):
        print(f"{i}. {message}")
    
    print(f"\n💾 最终AI回复: {result['ai_response']}")