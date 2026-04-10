
from core.llm_client import LLMClient


llm = LLMClient()
print(llm.call("我要周四的课程要请假"))