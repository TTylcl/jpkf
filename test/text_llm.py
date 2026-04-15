import requests
import os
from dotenv import load_dotenv
load_dotenv()

# 直接填你配置里的参数
API_KEY = os.getenv("LLM_API_KEY")
API_URL = os.getenv("LLM_BASE_URL")
MODEL_ID = os.getenv("LLM_MODEL")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": MODEL_ID,
    "messages": [{"role": "user", "content": "说一句测试"}],
    "temperature": 0.1,
    "max_tokens": 20
}

response = requests.post(API_URL, headers=headers, json=data, timeout=10)
print("状态码：", response.status_code)
print("返回内容：", response.text)