"""博客向量化入库编排。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import AiDocumentIndex
from app.services.blog_client import AdminContext, fetch_admin_blog_page, fetch_blog_detail
from app.services.chunk_service import split_markdown
from app.services.embedding_service import embed_query, embed_texts
from app.services.vector_store import SearchHit, get_vector_store

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.vector_store = get_vector_store()

    def submit_ingest_blog(self, blog_id: int) -> tuple[AiDocumentIndex, bool]:
        """
        提交单篇入库任务：标记 processing 并立即返回。
        返回 (record, should_run)：若已在 processing 则 should_run=False。
        """
        record = self._get_or_create_index(blog_id)
        if record.status == "processing":
            return record, False
        record.status = "processing"
        record.error_msg = None
        self.db.commit()
        self.db.refresh(record)
        return record, True

    def execute_ingest_blog(self, blog_id: int, admin_ctx: AdminContext) -> None:
        """后台执行：拉正文 → 切分 → Embedding → 写入 Qdrant。"""
        record = self._get_or_create_index(blog_id)
        if record.status != "processing":
            record.status = "processing"
            record.error_msg = None
            self.db.commit()

        try:
            blog = fetch_blog_detail(blog_id, admin_ctx)
            title = blog.get("title") or f"Blog #{blog_id}"
            content = blog.get("content") or ""
            publish_time = blog.get("publishTime") or blog.get("publish_time")
            source_url = f"/blogs/{blog_id}"

            record.title = title

            chunks = split_markdown(content)
            if not chunks:
                raise ValueError("博客正文为空，无法入库")

            self.vector_store.delete_by_blog_id(blog_id)
            vectors = embed_texts([chunk.text for chunk in chunks])
            self.vector_store.upsert_chunks(
                blog_id=blog_id,
                title=title,
                source_url=source_url,
                publish_time=str(publish_time) if publish_time else None,
                chunks=chunks,
                vectors=vectors,
            )

            record.status = "done"
            record.chunk_count = len(chunks)
            record.last_indexed_at = datetime.now()
            record.error_msg = None
            self.db.commit()
            logger.info("博客入库完成: blog_id=%s chunks=%s", blog_id, len(chunks))
        except Exception as exc:
            logger.exception("博客入库失败: blog_id=%s", blog_id)
            record.status = "failed"
            record.error_msg = str(exc)[:500]
            self.db.commit()

    def delete_blog_index(self, blog_id: int) -> None:
        self.vector_store.delete_by_blog_id(blog_id)
        record = (
            self.db.query(AiDocumentIndex)
            .filter(AiDocumentIndex.blog_id == blog_id)
            .one_or_none()
        )
        if record:
            record.status = "pending"
            record.chunk_count = 0
            record.error_msg = None
            record.last_indexed_at = None
            self.db.commit()

    def get_status(self, blog_id: Optional[int] = None) -> List[AiDocumentIndex]:
        query = self.db.query(AiDocumentIndex)
        if blog_id is not None:
            query = query.filter(AiDocumentIndex.blog_id == blog_id)
        return query.order_by(AiDocumentIndex.updated_at.desc()).all()

    def search(self, query: str, top_k: Optional[int] = None) -> List[SearchHit]:
        vector = embed_query(query)
        return self.vector_store.search(query_vector=vector, top_k=top_k)

    def execute_rebuild_blogs(
        self,
        admin_ctx: AdminContext,
        only_published: bool = True,
        skip_done: bool = False,
    ) -> dict:
        """后台批量入库。"""
        status_filter = 1 if only_published else None
        page = 1
        size = 50
        submitted = 0
        skipped = 0

        while True:
            page_data = fetch_admin_blog_page(
                admin_ctx,
                page=page,
                size=size,
                status=status_filter,
            )
            records = page_data.get("records") or []
            if not records:
                break

            for item in records:
                blog_id = int(item["id"])
                existing = (
                    self.db.query(AiDocumentIndex)
                    .filter(AiDocumentIndex.blog_id == blog_id)
                    .one_or_none()
                )
                if skip_done and existing and existing.status == "done":
                    skipped += 1
                    continue
                if existing and existing.status == "processing":
                    skipped += 1
                    continue
                self.execute_ingest_blog(blog_id, admin_ctx)
                submitted += 1

            total = int(page_data.get("total") or 0)
            if page * size >= total:
                break
            page += 1

        logger.info("批量入库完成: submitted=%s skipped=%s", submitted, skipped)
        return {"submitted": submitted, "skipped": skipped}

    def _get_or_create_index(self, blog_id: int) -> AiDocumentIndex:
        record = (
            self.db.query(AiDocumentIndex)
            .filter(AiDocumentIndex.blog_id == blog_id)
            .one_or_none()
        )
        if record is None:
            record = AiDocumentIndex(blog_id=blog_id, status="pending", chunk_count=0)
            self.db.add(record)
            self.db.flush()
        return record
