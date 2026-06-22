"""从 blog-service 拉取文章（Gateway 或内网直连）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings


@dataclass
class AdminContext:
    """Admin 调用 blog-service 的鉴权上下文（Gateway 注入 + 可选 JWT）。"""

    authorization: Optional[str] = None
    x_roles: Optional[str] = None
    x_user_id: Optional[str] = None

    def has_admin_access(self) -> bool:
        return bool(self.x_roles and "ADMIN" in self.x_roles)


def _api_base_url() -> str:
    """优先内网直连 blog-service，避免后台任务二次过 Gateway 时 JWT 失效。"""
    direct = (settings.blog_service_base_url or "").strip()
    if direct:
        return direct.rstrip("/")
    return settings.gateway_base_url.rstrip("/")


def _admin_headers(ctx: AdminContext) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if ctx.authorization:
        headers["Authorization"] = ctx.authorization
    if ctx.x_roles:
        headers["X-Roles"] = ctx.x_roles
    if ctx.x_user_id:
        headers["X-User-Id"] = ctx.x_user_id
    return headers


def _ensure_admin_ctx(ctx: AdminContext) -> None:
    if _api_base_url() != settings.gateway_base_url.rstrip("/"):
        if not ctx.has_admin_access():
            raise ValueError("批量拉取博客需要 Admin 角色（X-Roles）")
        return
    if not ctx.authorization:
        raise ValueError("批量拉取博客需要 Admin Token")


def fetch_blog_detail(blog_id: int, ctx: AdminContext) -> Dict[str, Any]:
    """
    拉取博客详情。
    有 Admin 上下文时走 admin 接口（含未发布）；否则走公开接口。
    """
    headers = _admin_headers(ctx)
    base = _api_base_url()

    if ctx.has_admin_access() or ctx.authorization:
        url = f"{base}/api/blogs/admin/{blog_id}"
    else:
        url = f"{base}/api/blogs/{blog_id}"

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers or None)
        response.raise_for_status()
        body = response.json()

    if body.get("code") != 200:
        raise ValueError(body.get("message") or "拉取博客失败")

    data = body.get("data")
    if not data:
        raise ValueError(f"博客 {blog_id} 不存在或无权限访问")
    return data


def fetch_admin_blog_page(
    ctx: AdminContext,
    page: int = 1,
    size: int = 100,
    status: Optional[int] = None,
) -> Dict[str, Any]:
    """Admin 博客分页列表（批量入库时使用）。"""
    _ensure_admin_ctx(ctx)

    params: Dict[str, Any] = {"page": page, "size": size}
    if status is not None:
        params["status"] = status

    url = f"{_api_base_url()}/api/blogs/admin"
    headers = _admin_headers(ctx)
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        body = response.json()

    if body.get("code") != 200:
        raise ValueError(body.get("message") or "拉取博客列表失败")
    return body.get("data") or {"records": [], "total": 0}
