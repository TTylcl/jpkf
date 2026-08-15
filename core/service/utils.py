# core/service/utils.py

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