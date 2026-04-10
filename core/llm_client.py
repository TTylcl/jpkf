
import os
import requests
from pathlib import Path
from core import settings
from dotenv import load_dotenv
from utils.logger import add_log
from core.prompt_templates.base_templates2 import EMOTIONAL_COMPANION_PROMPT_V1



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
        add_log("info", "---- LLMClient 初始化 ---")
        # 3. 初始化降级相关的参数：比如最大重试次数（3次）、熔断阈值（连续失败5次就直接降级）
        self.max_retry = settings.CIRCUIT_MAX_RETRY  # 最大重试次数
        self.circuit_breaker_threshold = settings.CIRCUIT_FAILURE_THRESHOLD # 熔断阈值
        #熔断提示
        self.circuit_breaker_message = settings.CIRCUIT_DEGRADE_MESSAGE
        #连续失败计数器
        #self.continuous_fail_count = settings.CONTINUOUS_FAIL_COUNT
        self.continuous_fail_count = 0
    def call(self, user_input: str) -> str: #input
        # 1. 打info日志：记录「开始调用大模型，用户输入内容：xxx」
        add_log("info", "开始调用大模型，用户输入内容：{}".format(user_input))
        # 2. 先判断熔断状态：如果已经触发熔断（连续失败超过阈值），直接返回兜底回复，不用发请求（对应你学的降级知识点）
        if self.circuit_breaker_threshold <= self.continuous_fail_count:
            add_log("warning",  f"触发熔断，连续失败次数：{self.continuous_fail_count}")
            return self.circuit_breaker_message
        # 3. 构造请求参数：按照你用的大模型的API文档填，和你之前构造天气API请求参数的逻辑一样
        # 1. 渲染Prompt模板，把占位符{user_input}替换成实际的用户输入
        rendered_prompt = EMOTIONAL_COMPANION_PROMPT_V1.format(user_input=user_input)
        # 2. 构造messages，把系统Prompt放在最前面，用户输入放后面
        messages = [
            {"role": "system", "content": rendered_prompt},
            {"role": "user", "content": user_input}
        ]
     
        # 构造请求参数
        params = {     
            "messages":messages, 
              
            "model": self.api_model,               
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }   
        # 4. 发请求：加超时控制，失败了就重试（最多重试3次，对应你学的重试知识点）
        for i in range(self.max_retry):
            try:
                # 发请求
                response = requests.post(url=self.api_url,headers=headers,json=params, timeout=self.timeout)
                # 检查响应状态码
                response.raise_for_status()  # 如果状态码不是200，抛出HTTPError
                # 获取响应结果
                
                result = response.json()
                # 获取大模型回复
                output = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        
                # 打info日志，记录「调用成功，耗时xxms，大模型回复：xxx」
                self.continuous_fail_count = 0
                # 6. 调用成功：连续失败计数器清0，打info日志记录「调用成功，耗时xxms，大模型回复：xxx」，把回复返回
                add_log("info", "调用成功，大模型回复：{}".format(output))
            
                return output
        # 5. 异常处理：不管是超时、限流、密钥错误、网络错误，都做三件事：
            # a. 打error日志，记录具体错误原因
            # b. 连续失败计数器+1，超过阈值就触发熔断
            # c. 返回预设的兜底回复（比如「哎呀我现在有点卡，你等会再和我说哦😘」，和你之前天气API调不通返回「暂时查不到天气」的逻辑完全一样）
            #except requests.exceptions.HTTPError as e:
            # 404``````````````````````````````   
             
            except Exception as e:
                
                self.continuous_fail_count += 1
                if self.circuit_breaker_threshold <= self.continuous_fail_count:
                    add_log("warning",  f"触发熔断，连续失败次数：{self.continuous_fail_count}")
                    return self.circuit_breaker_message
                else:
                    add_log("error", "请求失败，错误信息：{}".format(str(e)))
                    continue    
                    
       