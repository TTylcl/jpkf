
import os
import requests
from pathlib import Path
from core import settings
from dotenv import load_dotenv
from utils.logger import add_log
from core.prompt_templates.base_templates2 import EMOTIONAL_COMPANION_PROMPT_V1
from circuit.breaker import with_circuit_breaker,llm_breaker


load_dotenv()
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
class LLMClient:
    def __init__(self):
        # 1. 从pyprject.toml里读大模型的API_KEY、请求地址、超时时间（比如设10s，和你之前天气API的超时设置逻辑一样）
        self.api_key = os.getenv("LLM_API_KEY")
        self.api_url = os.getenv("LLM_BASE_URL")
        self.api_model = os.getenv("LLM_MODEL")
        #print(self.api_key)
        self.timeout = settings.PIPELINE_EXECUTE_TIMEOUT
        # 2. 初始化你刚写的日志工具，后面所有操作都打日志
        add_log("INFO", "---- LLMClient 初始化 ---")
        # 3. 初始化降级相关的参数：比如最大重试次数（3次）、熔断阈值（连续失败5次就直接降级）
        self.max_retry = settings.CIRCUIT_MAX_RETRY  # 最大重试次数
        self.circuit_breaker_threshold = settings.CIRCUIT_FAILURE_THRESHOLD # 熔断阈值
        #熔断提示
        self.circuit_breaker_message = settings.CIRCUIT_DEGRADE_MESSAGE
        #连续失败计数器
        #self.continuous_fail_count = settings.CONTINUOUS_FAIL_COUNT
        self.continuous_fail_count = 0

    #降级逻辑
    def _llm_fallback(self, messages: list,ctx=None,**kwargs) -> str:
        add_log("INFO", "LLMClient 降级处理",module='llm_client',ctx=ctx)
        return settings.CIRCUIT_DEGRADE_MESSAGE #默认的LLM的降级回复
    @with_circuit_breaker(breaker=llm_breaker,fallback_func=_llm_fallback)
    def call(self, messages: list[dict],temperature:float=0.1,max_tokens:int=500,ctx=None) -> str: #input
        # 1. 打info日志：记录「开始调用大模型，用户输入内容：xxx」
        add_log("INFO", f"开始调用大模：消息长度{len(messages)}",module='llm_client',ctx=ctx)
       
        #2 大模型请求
        for i in range(self.max_retry):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}", # API密钥
                    "Content-Type": "application/json", # 指定请求头
                    }
                json_data = {
                    "model": self.api_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                
 
                # 发请求
                response = requests.post(url=self.api_url,headers=headers,json=json_data, timeout=self.timeout)
               
                # 检查响应状态码
                response.raise_for_status()  # 如果状态码不是200，抛出HTTPError
                #print("--------------1-------------------")
                # 获取响应结果
                result = response.json()["choices"][0]["message"]["content"]
               
                #print("---------------2------------------")
                add_log("INFO", f"大模型返回：{result}",module='llm_client',ctx=ctx)
                return result
            except Exception as e:
                add_log("ERROR", f"大模型第{i+1}次重试失败：{str(e)}", module="llm_client", ctx=ctx)
                continue
        raise RuntimeError(f"大模型调用重试{self.max_retry}次全部失败")
