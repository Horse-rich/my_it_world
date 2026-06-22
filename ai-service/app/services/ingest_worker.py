"""后台执行博客向量化入库（独立 DB Session）。"""

from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.services.blog_client import AdminContext
from app.services.ingest_service import IngestService

logger = logging.getLogger(__name__)


def run_ingest_blog_task(blog_id: int, admin_ctx: AdminContext) -> None:
    db = SessionLocal()
    try:
        IngestService(db).execute_ingest_blog(blog_id, admin_ctx)
    except Exception:
        logger.exception("后台入库失败: blog_id=%s", blog_id)
    finally:
        db.close()


def run_rebuild_task(
    admin_ctx: AdminContext,
    only_published: bool = True,
    skip_done: bool = False,
) -> None:
    db = SessionLocal()
    try:
        IngestService(db).execute_rebuild_blogs(
            admin_ctx=admin_ctx,
            only_published=only_published,
            skip_done=skip_done,
        )
    except Exception:
        logger.exception("后台批量入库失败")
    finally:
        db.close()
