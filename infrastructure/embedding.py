# infrastructure/embedding.py
"""
【职责】创建 Embedding 模型实例，与 LLM 工厂平级
【设计原则】
  1. 工厂模式：和 llm.py 一致，只管创建，不管业务
  2. 配置外部注入：模型名从 env 读取
  3. 单例复用：全局只创建一次
  4. 使用 OpenAI SDK 调用 MaaS API，继承 LangChain Embeddings 基类，避免 OpenAIEmbeddings 的 tiktoken 问题
  【使用方式】
    from infrastructure.embedding import create_embedding
    embedding = create_embedding()
    vectors = embedding.embed_documents(["退费规则", "课程介绍"])
    vector = embedding.embed_query("退费要多久")
"""
import os
from typing import List

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from openai import OpenAI

load_dotenv()

_embedding_instance = None  # 单例


class MaaSEmbeddings(Embeddings):
    """MaaS 百炼 Embedding 客户端 —— 使用 OpenAI SDK，兼容 OpenAI 格式 API"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def embed_query(self, text: str) -> List[float]:
        """嵌入单条查询文本"""
        resp = self.client.embeddings.create(model=self.model, input=[text])
        return resp.data[0].embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


def create_embedding() -> MaaSEmbeddings:
    """创建 Embedding 模型实例（MaaS 兼容接口）"""
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    api_key = os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY"))
    base_url = os.getenv("EMBEDDING_BASE_URL", os.getenv("LLM_BASE_DATA_URL"))
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")

    print("===============创建 Embedding 模型实例 (MaaS)=====================")
    print(f"  API: {base_url}")
    print(f"  Model: {model}")

    _embedding_instance = MaaSEmbeddings(api_key=api_key, base_url=base_url, model=model)
    return _embedding_instance