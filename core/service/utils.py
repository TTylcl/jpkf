# core/service/utils.py

# ── 预排课时间解析：把自由文本「周X HH:MM-HH:MM」转结构化字段 ──
_DAY_MAP = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7,
            "星期一": 1, "星期二": 2, "星期三": 3, "星期四": 4, "星期五": 5, "星期六": 6, "星期日": 7}


def parse_preferred_time(preferred_time: str) -> dict | None:
    """把自由文本期望时间解析成结构化字段

    步骤：
    1. 正则匹配「周X / 星期X HH:MM[-~至到]HH:MM」
    2. 星期几映射成 1-7
    3. 起止时间字符串 → datetime.time 对象

    返回 {"day_of_week": int, "start_time": time, "end_time": time}，解析失败返回 None。
    调用方自行决定「跳过」还是「报错」——提交时应报错，冲突检查时才跳过。
    """
    import re
    from datetime import time as dt_time

    m = re.match(r"(周[一二三四五六日]|星期[一二三四五六日])\s*(\d{1,2}:\d{2})\s*[-~至到]\s*(\d{1,2}:\d{2})", preferred_time)
    if not m:
        return None
    day_str, start_str, end_str = m.groups()
    day_of_week = _DAY_MAP.get(day_str)
    if day_of_week is None:
        return None
    try:
        start_parts = start_str.split(":")
        end_parts = end_str.split(":")
        start_time = dt_time(int(start_parts[0]), int(start_parts[1]))
        end_time = dt_time(int(end_parts[0]), int(end_parts[1]))
    except (ValueError, IndexError):
        return None
    return {"day_of_week": day_of_week, "start_time": start_time, "end_time": end_time}


def get_dao(ctx, dao_class):
    """从 CTX 获取 DAO 实例"""
    return dao_class(ctx.session)


def mask_sensitive(data, agent_role):
    """脱敏敏感字段"""
    if not data or agent_role == "edu_admin_agent":
        return data

    if isinstance(data, dict):
        masked = data.copy()
        if "phone" in masked and isinstance(masked.get("phone"), str) and len(masked["phone"]) > 7:
            masked["phone"] = masked["phone"][:3] + "****" + masked["phone"][-4:]
        if "email" in masked and isinstance(masked.get("email"), str) and "@" in masked["email"]:
            name, domain = masked["email"].split("@", 1)
            masked["email"] = (name[:2] if len(name) > 2 else name) + "***@" + domain
        return masked

    return data