"""知识库访问权限 API。"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user_id, require_admin
from app.db.session import get_db
from app.models.schemas import (
    KnowledgeAccessData,
    KnowledgeSettingsData,
    KnowledgeSettingsUpdateRequest,
    Result,
)
from app.services.knowledge_settings_service import KnowledgeSettingsService

router = APIRouter(prefix="/api/ai/knowledge", tags=["AI-Knowledge"])


@router.get("/access", response_model=Result)
def knowledge_access(
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> Result:
    """
    公开：查询当前用户是否可使用知识库（RAG）。
    游客看 guestRagEnabled；登录用户看 userRagEnabled。
    """
    payload = KnowledgeSettingsService(db).to_access_payload(user_id)
    data = KnowledgeAccessData(**payload)
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))


@router.get("/settings", response_model=Result)
def get_knowledge_settings(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Result:
    """Admin：读取知识库访问权限配置。"""
    record = KnowledgeSettingsService(db).get_settings()
    data = KnowledgeSettingsData(
        guestRagEnabled=bool(record.guest_rag_enabled),
        userRagEnabled=bool(record.user_rag_enabled),
        updatedAt=record.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        if record.updated_at
        else None,
    )
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))


@router.put("/settings", response_model=Result)
def update_knowledge_settings(
    request: KnowledgeSettingsUpdateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Result:
    """Admin：更新游客/登录用户的知识库使用权限。"""
    record = KnowledgeSettingsService(db).update_settings(
        guest_rag_enabled=request.guestRagEnabled,
        user_rag_enabled=request.userRagEnabled,
    )
    data = KnowledgeSettingsData(
        guestRagEnabled=bool(record.guest_rag_enabled),
        userRagEnabled=bool(record.user_rag_enabled),
        updatedAt=record.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        if record.updated_at
        else None,
    )
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))
