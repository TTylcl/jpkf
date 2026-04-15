from dotenv import load_dotenv
load_dotenv()
import sys

from pathlib import Path
sys.path.append(Path(__file__).parent.parent.as_posix())

from utils.logger import add_log
from core.llm_client import LLMClient

def test_llm_normal_call():
    """测试LLM真实连通性"""
    llm_client = LLMClient()
    test_messages = [{"role": "user", "content": "请只回复“LLM连通性正常”，不要其他内容"}]
    t_messages = [{"role": "user", "content": "你是谁"}]
    print(f"开始调用大模型，消息长度：{len(test_messages)}")
    add_log("INFO", f"开始调用大模：消息长度{len(test_messages)}",module='llm_client')
    result = llm_client.call(messages=t_messages, temperature=0.0, max_tokens=20)
    print(f"返回结果：{result}")
    add_log("INFO", f"返回结果：{result}",module='llm_client')
    assert "LLM连通性正常" in result, f"返回结果不符合预期：{result}"
if __name__ == "__main__":
    test_llm_normal_call()