
#test/test_graph.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import asyncio
from core.context import AgentContext
from core.graph.nodes.generate_node import generate_reply_node
from utils.logger import add_log
from core.graph.chat_graph import build_chat_graph
from core.get_llm_client import get_llm_client
async def test_chat():
    print("开始测试...")
   
    print("开始测试langgraph...")
    #用户测试
    print("正常用户张三妈妈测试...")
    ctx = AgentContext(user_id="张三妈妈", user_input="我孩子剩下多少数学课",llm_client=get_llm_client)
    initial_state = {
        "ctx": ctx, 
        "messages":[{"role": "user", "content": "我孩子剩下多少数学课"}] }
    # 2. 构建Graph
    chat_graph =build_chat_graph()#
    # 3. 执行Graph
   
    add_log(result["ctx"].logs)
    print("\n开始执行Graph...")
    result = await chat_graph.ainvoke(
        initial_state,
        config={"recursion_limit": 10}
    )
    # ✅ 只打印核心字段，不要直接打印整个State
    print("\n✅ 执行完成！")
    print(f"结果：{result['generated_reply']}")
if __name__ == "__main__":
    # 可以先跑单节点，再跑整个Graph
    asyncio.run(test_chat())
