"""FastAPI 依赖：从 Gateway 转发的请求头解析用户信息。"""

from typing import Optional

from fastapi import Depends, Header, HTTPException


async def get_optional_user_id(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> Optional[int]:
    """解析 Gateway JWT 过滤器注入的用户 ID；游客或未登录时为 None。"""
    if not x_user_id or not x_user_id.strip():
        return None
    try:
        return int(x_user_id)
    except ValueError:
        return None


async def require_admin(
    x_roles: Optional[str] = Header(default=None, alias="X-Roles"),
) -> None:
    """校验 Gateway 注入的角色头，ingest 接口需 ADMIN。"""
    if not x_roles or "ADMIN" not in x_roles:
        raise HTTPException(status_code=403, detail="需要管理员权限")


async def get_authorization(
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    """透传 Authorization，供拉取 blog admin 详情。"""
    return authorization


async def get_admin_context(
    authorization: Optional[str] = Depends(get_authorization),
    x_roles: Optional[str] = Header(default=None, alias="X-Roles"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> "AdminContext":
    """Gateway 校验 JWT 后注入的管理员上下文，供后台入库任务使用。"""
    from app.services.blog_client import AdminContext

    return AdminContext(
        authorization=authorization,
        x_roles=x_roles,
        x_user_id=x_user_id,
    )
