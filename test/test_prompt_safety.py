"""
test/test_prompt_safety.py

Prompt 安全测试：验证所有会被 system_prompt.format() 的 Prompt 都能安全格式化。

背景：PARENT_SERVICE_PROMPT 曾因 {课程名} / {教师名} 未转义，导致
      .format(agent_role=..., user_role=...) 抛 KeyError，所有角色全部请求崩溃。
      此测试防止同类回归。
"""
import pytest

from core.prompt_templates.base_templates import (
    ADMIN_PROMPT,
    TEACHER_PROMPT,
    PARENT_SERVICE_PROMPT,
    STUDENT_PROMPT,
    SCHEDULE_AGENT_PROMPT,
    RAG_AGENT_PROMPT,
)

# 所有在 core/graph/builder.py 中通过 create_agent_node 传入、
# 并在 core/graph/nodes/agent_node.py 中被 .format(agent_role, user_role) 的 prompt
FORMATTED_PROMPTS = {
    "ADMIN_PROMPT": ADMIN_PROMPT,
    "TEACHER_PROMPT": TEACHER_PROMPT,
    "PARENT_SERVICE_PROMPT": PARENT_SERVICE_PROMPT,
    "STUDENT_PROMPT": STUDENT_PROMPT,
    "SCHEDULE_AGENT_PROMPT": SCHEDULE_AGENT_PROMPT,
    "RAG_AGENT_PROMPT": RAG_AGENT_PROMPT,
}


@pytest.mark.parametrize("name", sorted(FORMATTED_PROMPTS))
def test_prompt_format_is_safe(name):
    """每个 prompt 都能安全 .format(agent_role, user_role)，不抛 KeyError/ValueError"""
    prompt = FORMATTED_PROMPTS[name]

    result = prompt.format(agent_role="test_role", user_role="test_user")

    assert isinstance(result, str)
    assert result.strip(), f"{name} 格式化结果为空"
    # 占位符必须被完全替换，不允许残留未替换的 {agent_role} / {user_role}
    assert "{agent_role}" not in result, f"{name} 残留未替换的 {{agent_role}}"
    assert "{user_role}" not in result, f"{name} 残留未替换的 {{user_role}}"
