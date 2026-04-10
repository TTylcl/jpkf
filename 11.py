# core/llm_client.py 伪代码结构
import requests
import time
from utils.logger import logger
from config.settings import settings
class LLMClient:
    def __init__(self):
        # 所有参数都从settings读，不硬编码
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url
        self.timeout = settings.llm_timeout
        self.max_retry = settings.llm_max_retry
        self.circuit_breaker_threshold = settings.llm_circuit_breaker
        
        # 内部维护熔断计数器，不用存在外面
        self._continuous_fail_count = 0
    def call(self, user_input: str) -> str:
        """
        只接收用户输入，返回大模型回复，所有异常都内部处理，绝对不抛给上层
        """
        # 1. 先判断熔断：如果连续失败超过阈值，直接返回兜底，不用发请求
        if self._continuous_fail_count >= self.circuit_breaker_threshold:
            logger.warning(f"触发熔断，连续失败{self._continuous_fail_count}次，直接返回兜底")
            return settings.fallback_reply
        
        # 2. 重试循环，最多试max_retry次
        for retry_idx in range(self.max_retry):
            start_time = time.time()
            try:
                # 👇 这里写你调用大模型API的逻辑，和你之前调天气API完全一样
                # 构造请求头（带API密钥）、请求体（按你用的大模型文档写，比如model、messages、temperature）
                # 发POST请求，加timeout=self.timeout
                # 解析返回结果，拿到大模型的回复内容
                
                # 调用成功的逻辑
                self._continuous_fail_count = 0 # 清零失败计数器
                cost_time = round((time.time() - start_time)*1000, 2)
                logger.info(f"大模型调用成功，重试次数：{retry_idx}，耗时：{cost_time}ms，输入：{user_input[:50]}，回复：{reply[:50]}")
                return reply
            except Exception as e:
                cost_time = round((time.time() - start_time)*1000, 2)
                logger.error(f"大模型调用失败，第{retry_idx+1}次重试，耗时：{cost_time}ms，错误原因：{str(e)}")
                # 最后一次重试也失败了，累加失败计数器
                if retry_idx == self.max_retry -1:
                    self._continuous_fail_count +=1
                    logger.error(f"所有重试都失败，连续失败次数：{self._continuous_fail_count}")
                    return settings.fallback_reply
                # 不是最后一次，等1秒再重试（避免触发API限流）
                time.sleep(1)