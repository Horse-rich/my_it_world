"""知识库入库与检索验收 API（Admin）。"""

from __future__ import annotations

import time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_admin_context, require_admin
from app.services.blog_client import AdminContext
from app.db.session import get_db
from app.models.schemas import (
    DocumentIndexStatus,
    IngestBlogResult,
    IngestRebuildRequest,
    IngestRebuildResult,
    IngestSearchHit,
    IngestSearchRequest,
    Result,
)
from app.services.ingest_service import IngestService
from app.services.ingest_worker import run_ingest_blog_task, run_rebuild_task
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/ai/ingest", tags=["AI-Ingest"])


def _format_dt(value) -> Optional[str]:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _to_status(item) -> DocumentIndexStatus:
    return DocumentIndexStatus(
        blogId=item.blog_id,
        title=item.title,
        status=item.status,
        chunkCount=item.chunk_count,
        errorMsg=item.error_msg,
        lastIndexedAt=_format_dt(item.last_indexed_at),
        updatedAt=_format_dt(item.updated_at),
    )


@router.post("/blog/{blog_id}", response_model=Result)
def ingest_blog(
    blog_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
    admin_ctx: AdminContext = Depends(get_admin_context),
) -> Result:
    """提交单篇博客入库任务（异步），立即返回 processing 状态。"""
    svc = IngestService(db)
    record, should_run = svc.submit_ingest_blog(blog_id)
    if should_run:
        background_tasks.add_task(run_ingest_blog_task, blog_id, admin_ctx)
        message = "入库任务已下发，请稍后点击刷新查看索引状态"
    else:
        message = "该博客正在入库中，请稍后点击刷新查看状态"
    data = IngestBlogResult(
        blogId=record.blog_id,
        title=record.title,
        status=record.status,
        chunkCount=record.chunk_count,
        lastIndexedAt=_format_dt(record.last_indexed_at),
    )
    return Result(code=200, message=message, data=data, timestamp=int(time.time() * 1000))


@router.post("/rebuild", response_model=Result)
def rebuild_blogs(
    background_tasks: BackgroundTasks,
    request: IngestRebuildRequest | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
    admin_ctx: AdminContext = Depends(get_admin_context),
) -> Result:
    """提交批量入库任务（异步），立即返回。"""
    if request is None:
        request = IngestRebuildRequest()
    background_tasks.add_task(
        run_rebuild_task,
        admin_ctx,
        request.onlyPublished,
        request.skipDone,
    )
    data = IngestRebuildResult(success=0, failed=0, skipped=0, errors=[])
    return Result(
        code=200,
        message="批量入库任务已下发，请稍后点击刷新查看各博客索引状态",
        data=data,
        timestamp=int(time.time() * 1000),
    )


@router.delete("/blog/{blog_id}", response_model=Result)
def delete_blog_index(
    blog_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Result:
    """删除某篇博客的向量索引。"""
    IngestService(db).delete_blog_index(blog_id)
    return Result(code=200, message="success", data={"blogId": blog_id}, timestamp=int(time.time() * 1000))


@router.get("/status", response_model=Result)
def ingest_status(
    blog_id: Optional[int] = Query(default=None, alias="blogId"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Result:
    """查询入库状态（可按 blogId 过滤）。"""
    items = IngestService(db).get_status(blog_id)
    data: List[DocumentIndexStatus] = [_to_status(item) for item in items]
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))


@router.post("/search", response_model=Result)
def ingest_search(
    request: IngestSearchRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Result:
    """检索验收（不做 LLM 生成）。"""
    hits = IngestService(db).search(request.query, top_k=request.topK)
    data = [
        IngestSearchHit(
            score=h.score,
            blogId=h.blog_id,
            title=h.title,
            chunkIndex=h.chunk_index,
            sourceUrl=h.source_url,
            text=h.text,
            publishTime=h.publish_time,
        )
        for h in hits
    ]
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))


@router.get("/health", response_model=Result)
def ingest_health() -> Result:
    """Qdrant 与向量库概况。"""
    store = get_vector_store()
    try:
        store.ensure_collection()
        point_count = store.count_points()
        qdrant_ok = True
        error = None
    except Exception as exc:
        qdrant_ok = False
        point_count = 0
        error = str(exc)

    return Result(
        code=200,
        message="success",
        data={
            "qdrantOk": qdrant_ok,
            "collection": store.collection,
            "pointCount": point_count,
            "error": error,
        },
        timestamp=int(time.time() * 1000),
    )
