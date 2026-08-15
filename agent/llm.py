"""
LLM 工具绑定
职责：创建 ChatModel 实例，使用 bind_tools 方法绑定上一步收集的工具列表，
      使 LLM 能根据描述和 schema 决定调用工具。
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel


def create_chat_model(temperature: float = 0.1) -> ChatOpenAI:
    """
    创建 ChatModel 实例
    从 .env 读取配置：API Key、Base URL、Model Name
    """
    load_dotenv()
    
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_DATA_URL")
    model_name = os.getenv("LLM_MODEL")
    
    print("=" * 60)
    print("🔧 创建 ChatModel 实例")
    print("=" * 60)
    print(f"模型名称：{model_name}")
    print(f"API 地址：{base_url}")
    print(f"温度参数：{temperature}")
    
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=temperature,
        streaming=True,  # 开启流式输出
    )


def bind_tools_to_llm(temperature: float = 0.1, agent_role: str | None = None,tool_names: list[str] | None = None) -> BaseChatModel:
    """
    完整的 LLM 工具绑定流程
    1. 创建 ChatModel 实例
    2. 调用 build_langchain_tools(agent_role) 获取工具列表（按角色过滤）
    3. 执行 model.bind_tools(tools) 将工具绑定到模型
    4. 返回绑定后的 model，供 agent 节点使用

    Args:
        temperature: LLM 温度参数
        agent_role: 可选，按角色过滤工具（None = 不过滤）
        tool_names: 可选，指定工具名称列表（None = 使用所有工具）
    """
    # 1. 创建 ChatModel 实例
    model = create_chat_model(temperature)

    # 2. 获取工具列表（按角色过滤）
    from core.graph.tools.loader import build_langchain_tools
    tools = build_langchain_tools(agent_role=agent_role,tool_names=tool_names)

    # 3. 执行 bind_tools 将工具绑定到模型
    print(f"\n🔗 绑定 {len(tools)} 个工具到 LLM...")
    model_with_tools = model.bind_tools(tools)

    print("=" * 60)
    print("✅ LLM 工具绑定完成")
    print("=" * 60)

    # 4. 返回绑定后的 model
    return model_with_tools


# 别名：兼容其他地方的导入
get_llm_with_tools = bind_tools_to_llm

__all__ = ["create_chat_model", "bind_tools_to_llm", "get_llm_with_tools","build_langchain_tools"]


# 单独运行测试
if __name__ == "__main__":
    model = bind_tools_to_llm()