"""
api/routers/auth_router.py
认证路由：登录签发 JWT + 提供 get_current_user 鉴权依赖

本文件是整个系统鉴权的入口，一共两件事：
1. 【接口】POST /api/auth/login —— 用户名密码换 token
2. 【依赖】get_current_user —— 供其他路由挂载，校验 token 并返回当前用户身份

鉴权模型（面试可讲）：
- 无状态 JWT：服务端不存 session，token 里自含身份信息，靠签名防篡改
- 客户端每次请求带 `Authorization: Bearer <token>` 头
- 服务端依赖 get_current_user 解签名 → 得到 user_id / user_type
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from core.database import AsyncDatabase
from core.security import create_access_token, decode_access_token, verify_password
from dal.dao.user_dao import UserDao

router = APIRouter(tags=["auth"])

# 解析请求头里的 `Authorization: Bearer <token>`
# auto_error=False：头缺失时不立刻抛错，而是返回 None，交给 get_current_user 统一处理
bearer_scheme = HTTPBearer(auto_error=False)


# ══════════════════════════════════════════════════
# 【请求 / 响应模型】
# ══════════════════════════════════════════════════
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    code: int = 200
    message: str = "登录成功"
    token: str = ""        # 签发的 JWT，前端保存后每次请求带上
    user_id: int = 0
    user_type: str = ""


# ══════════════════════════════════════════════════
# 【功能 1】登录接口
# ══════════════════════════════════════════════════
@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """用户名密码登录，成功后签发 JWT。

    步骤：
    1. 按 username 查库（get_by_username）
    2. 校验密码：用户不存在 / 密码不匹配 → 统一返回 401
    3. 校验通过 → 用 user_id + user_type + username 签发 token
    """
    async with AsyncDatabase.get_session() as session:
        user = await UserDao(session).get_by_username(req.username)

    # 安全细节：两种失败返回同一条错误信息，避免攻击者枚举出哪些用户名存在
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user.user_id, user.user_type.value, user.username)
    return LoginResponse(token=token, user_id=user.user_id, user_type=user.user_type.value)


# ══════════════════════════════════════════════════
# 【功能 2】鉴权依赖（其他接口挂 Depends(get_current_user) 即可受保护）
# ══════════════════════════════════════════════════
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """从 Authorization 头解析并校验 token，返回当前用户身份。

    步骤：
    1. 头里没有 token（credentials 为 None）→ 401「未提供认证信息」
    2. decode_access_token 解签名；签名错 / 过期 / 被篡改 → 抛异常 → 401「认证信息无效」
    3. payload 里缺 user_id / user_type → 401「token 内容不完整」
    4. 通过 → 返回 {"user_id", "user_type"}，供业务路由使用

    为什么身份只从 token 读：修复 IDOR。之前业务接口信任请求体传的 user_id，
    攻击者改个 id 就能冒充别人；现在身份统一由签名 token 决定，传参不再生效。
    """
    # 步骤 1：无凭证
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证信息")

    # 步骤 2：验签失败（签名错 / 过期 / 被篡改都会抛异常）
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="认证信息无效")

    # 步骤 3：payload 缺关键字段
    user_id = payload.get("user_id")
    user_type = payload.get("user_type")
    if not user_id or not user_type:
        raise HTTPException(status_code=401, detail="token 内容不完整")

    # 步骤 4：返回当前用户身份
    return {"user_id": int(user_id), "user_type": user_type}
