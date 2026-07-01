"""RAG 检索与上下文组装。"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.ingest_service import IngestService
from app.services.knowledge_settings_service import KnowledgeSettingsService
from app.services.vector_store import SearchHit

logger = logging.getLogger(__name__)

_RAG_INSTRUCTION = (
    "以下是本站博客中与用户问题相关的参考资料。请优先基于这些内容回答；"
    "若资料不足以完整回答，可结合通用知识补充，并明确说明哪些来自博客、哪些为通用推断。"
    "回答请简洁清晰，使用中文。"
)


def hits_to_sources(hits: List[SearchHit]) -> List[dict]:
    """检索命中 → 前端引用卡片（同一 blog 只保留相似度最高的一条）。"""
    best_by_blog: dict[int, SearchHit] = {}
    for hit in hits:
        existing = best_by_blog.get(hit.blog_id)
        if existing is None or hit.score > existing.score:
            best_by_blog[hit.blog_id] = hit

    sources: List[dict] = []
    for hit in sorted(best_by_blog.values(), key=lambda h: h.score, reverse=True):
        sources.append(
            {
                "blogId": hit.blog_id,
                "title": hit.title,
                "sourceUrl": hit.source_url,
                "chunkIndex": hit.chunk_index,
                "score": round(hit.score, 4),
            }
        )
    return sources


def format_rag_context(hits: List[SearchHit]) -> str:
    """将命中片段格式化为可注入 system prompt 的文本块。"""
    parts: List[str] = [_RAG_INSTRUCTION, ""]
    for index, hit in enumerate(hits, start=1):
        parts.append(f"【片段 {index}】")
        parts.append(f"标题：{hit.title}")
        parts.append(f"链接：{hit.source_url}")
        if hit.publish_time:
            parts.append(f"发布时间：{hit.publish_time}")
        parts.append(f"内容：{hit.text.strip()}")
        parts.append("")
    return "\n".join(parts).strip()


class RagService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ingest = IngestService(db)
        self.settings_svc = KnowledgeSettingsService(db)

    def retrieve(
        self,
        user_id: Optional[int],
        query: str,
        top_k: Optional[int] = None,
    ) -> Tuple[List[SearchHit], List[dict], Optional[str], bool]:
        """
        按权限检索知识库。
        返回 (hits, sources, rag_context, rag_enabled)。
        rag_enabled 表示本次请求是否启用了 RAG（与是否命中无关）。
        """
        rag_allowed = self.settings_svc.is_rag_allowed(user_id)
        if not rag_allowed:
            return [], [], None, False

        try:
            hits = self.ingest.search(query, top_k=top_k)
        except Exception as exc:
            logger.warning("RAG 向量检索失败，尝试关键词兜底: %s", exc, exc_info=True)
            hits = self.ingest.keyword_search(query, top_k=top_k)
            if not hits:
                err_ctx = (
                    f"[RAG_ERROR] Embedding 或向量检索失败: {exc}。"
                    "请说明检索服务暂时不可用，勿声称 hits=0。"
                )
                return [], [], err_ctx, True

        if settings.rag_min_score > 0:
            hits = [h for h in hits if h.score >= settings.rag_min_score]
        if not hits:
            return [], [], None, True
        sources = hits_to_sources(hits)
        context = format_rag_context(hits)
        return hits, sources, context, True
