
from utils.logger import add_log


def generate_reply_node(state: dict)->dict:
    user_input = state["user_input"]
    logger = add_log("f[生成节点]输入：{user_input}")
    reply = LLMClient_client.call(user_input)