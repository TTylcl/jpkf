
from core.prompt_templates.base_templates import EDUCATION_CUSTOMER_SERVICE_PROMPT_V1
    

@staticmethod
def build_education_customer_service_prompt(user_info: dict, user_input: str) -> str:
    """构建教育客服Prompt"""
    context = (
        f"📊 用户ID：{user_info.get('user_id', '未知')} | "
        f"孩子姓名：{user_info.get('孩子姓名', '未知')} | "
        f"英语课时：{user_info.get('英语课时', 0)}节 | "
        f"数学课时：{user_info.get('数学课时', 0)}节"
    )
    
    return EDUCATION_CUSTOMER_SERVICE_PROMPT_V1.format(
        context=context,
        user_input=user_input
    )