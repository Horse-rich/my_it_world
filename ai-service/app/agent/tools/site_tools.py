"""站内业务工具：RAG 检索、博客元数据。"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.agent.tools.base import BaseTool
from app.agent.tools.context import ToolContext
from app.agent.tools.weather_tool import WeatherTool
from app.services.blog_client import AdminContext, fetch_blog_detail
from app.services.rag_service import RagService


class SearchBlogChunksTool(BaseTool):
    name = "search_blog_chunks"
    description = (
        "在本站已入库博客中做语义检索，返回与问题相关的文章片段。"
        "适用于站内任意已发布/已入库内容：技术文章、运维笔记、个人介绍、站点说明等。"
        "当用户提到「根据博客」「知识库」「站内文章」或询问某主题是否在博客中出现时，应优先调用。"
    )
    parameters: Dict[str, Any] = {
        "query": {
            "type": "string",
            "description": "检索关键词或自然语言问题",
            "required": True,
        },
        "top_k": {
            "type": "integer",
            "description": "返回片段数量，默认 5",
            "required": False,
        },
    }

    def __init__(self, ctx: ToolContext) -> None:
        self._ctx = ctx

    def execute(self, query: str, top_k: int = 5) -> str:
        rag = RagService(self._ctx.db)
        _, sources, context, rag_enabled = rag.retrieve(
            self._ctx.user_id, query.strip(), top_k=top_k
        )
        if not rag_enabled:
            return (
                "[RAG_DISABLED] 当前用户未开启知识库检索权限（游客需开启 guestRagEnabled，"
                "登录用户需开启 userRagEnabled）。请勿声称已检索到空结果，应说明权限未开启。"
            )

        for item in sources:
            if item not in self._ctx.collected_sources:
                self._ctx.collected_sources.append(item)

        if not context:
            return (
                "[RAG_EMPTY] 向量库检索已完成，但未命中相关片段（hits=0）。"
                "可说明未找到，勿编造检索过程以外的内容。"
            )

        if context.startswith("[RAG_ERROR]"):
            return context

        return context


class GetBlogMetadataTool(BaseTool):
    name = "get_blog_metadata"
    description = "根据博客 ID 获取文章标题与正文摘要。"
    parameters: Dict[str, Any] = {
        "blog_id": {
            "type": "integer",
            "description": "博客文章 ID",
            "required": True,
        },
    }

    def __init__(self, ctx: ToolContext) -> None:
        self._ctx = ctx

    def execute(self, blog_id: int) -> str:
        admin = self._ctx.admin_ctx or AdminContext()
        blog = fetch_blog_detail(int(blog_id), admin)
        title = blog.get("title") or f"Blog #{blog_id}"
        content = (blog.get("content") or "")[:2000]
        return json.dumps(
            {
                "blogId": blog_id,
                "title": title,
                "contentPreview": content,
                "sourceUrl": blog.get("sourceUrl") or f"/blogs/{blog_id}",
            },
            ensure_ascii=False,
        )


class DateTimeTool(BaseTool):
    name = "datetime"
    description = "获取当前日期和时间。"
    parameters: Dict[str, Any] = {
        "format": {
            "type": "string",
            "description": "日期格式，默认 %Y-%m-%d %H:%M:%S",
            "required": False,
        },
    }

    def execute(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        from datetime import datetime

        now = datetime.now()
        return f"当前时间: {now.strftime(format)} ({now.strftime('%A')})"


def build_site_assistant_tools(ctx: ToolContext) -> list[BaseTool]:
    return [
        SearchBlogChunksTool(ctx),
        GetBlogMetadataTool(ctx),
        WeatherTool(),
        DateTimeTool(),
    ]
