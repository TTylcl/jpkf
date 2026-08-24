"""/core/security.py
安全工具层：密码哈希 + JWT 签发与校验

职责边界（单一职责）：
- 本模块只负责「密码怎么加密」「token 怎么生成/验证」两个原子能力
- 不做业务判断（用户是否存在、有没有权限），那些交给 auth_router / service 层
- 对外暴露 4 个纯函数，无状态、无数据库依赖，方便单独测试

依赖说明：
- bcrypt：密码哈希（自带盐值 + 慢哈希，抗彩虹表）
- PyJWT：JWT 的编解码 + 签名校验
"""
from __future__ import annotations  # 类型注解延迟求值

from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from core import settings


# ══════════════════════════════════════════════════
# 【功能 1】密码哈希 —— 明文密码绝不落库
# ══════════════════════════════════════════════════

def hash_password(plain: str) -> str:
    """把明文密码转成 bcrypt 哈希值（注册 / 回填密码时调用）

    步骤：
    1. 明文编码成字节
    2. bcrypt.gensalt() 随机生成盐值（每次不同，所以同一密码两次哈希结果不同）
    3. hashpw 做慢哈希，返回 60 字符的哈希串
    """
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    """校验「明文密码」和「库里的哈希」是否匹配（登录时调用）

    步骤：
    1. 哈希为空（老数据没设密码）→ 直接 False，杜绝绕过
    2. bcrypt.checkpw 重新哈希明文再比对，相等返回 True
    3. 捕获 ValueError / TypeError：库里哈希格式非法时不抛异常，而是返回 False
    """
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ══════════════════════════════════════════════════
# 【功能 2】JWT —— 登录后签发、每次请求校验
# ══════════════════════════════════════════════════

def create_access_token(user_id: int, user_type: str, username: str) -> str:
    """签发 JWT 访问令牌（登录成功后调用）

    步骤：
    1. 计算过期时间 = 当前 UTC 时间 + settings.JWT_EXPIRE_DAYS 天
    2. 组装 payload（只放必要、非敏感的身份信息，绝不放大段隐私数据）
    3. jwt.encode 用 JWT_SECRET 做 HS256 签名，返回三段式 token

    参数：
        user_id   用户主键，鉴权据此识别「是谁」
        user_type 角色：ADMIN / TEACHER / PARENT / STUDENT，据此路由到不同 Agent
        username  用户名，仅作日志 / 调试辅助
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "user_type": user_type,
        "username": username,
        "exp": expire,   # 标准过期字段，PyJWT 会自动校验
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """校验并解码 token，返回 payload

    说明：
    - 签名不对 / 已过期 / 被篡改时，jwt.decode 会抛异常（PyJWT 的 InvalidTokenError 系列）
    - 本函数不捕获异常，故意让它抛出去，由调用方（get_current_user）统一转成 401
    - 这样「验签失败」和「业务失败」在职责上分得清清楚楚
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
