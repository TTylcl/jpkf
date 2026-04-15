import requests

# 直接写死你正确的配置
API_KEY = "sk-bW5suYjQXDrvbtgMD666523072C8452aB5D40e260b561880"
API_URL = "https://ai-yyds.com/v1/chat/completions"
MODEL = "deepseek-chat"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "你好"}]
}

print("开始请求...")
response = requests.post(API_URL, headers=headers, json=data)

print("状态码:", response.status_code)
print("返回结果:", response.text)