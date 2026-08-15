"""测试 ai-yyds.com 是否支持 embedding 接口"""
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embedding = OpenAIEmbeddings(
    openai_api_key=os.getenv("LLM_API_KEY"),
    openai_api_base=os.getenv("LLM_BASE_DATA_URL"),
    model="text-embedding-3-small",
)

try:
    result = embedding.embed_query("测试")
    print(f"✅ 成功！向量维度: {len(result)}")
except Exception as e:
    print(f"❌ 失败: {e}")