"""会话列表、历史消息、删除与改标题。"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user_id
from app.db.session import get_db
from app.models.schemas import (
    ChatMessage,
    Result,
    SessionListData,
    SessionMessagesData,
    SessionSummary,
    UpdateSessionRequest,
)
from app.services.message_store import ChatMessageStore
from app.services.session_service import ChatSessionService

router = APIRouter(prefix="/api/ai/sessions", tags=["AI Sessions"])


def _format_dt(value: datetime) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


@router.get("", response_model=Result)
def list_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> Result:
    """我的会话列表（需登录）。"""
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")

    session_svc = ChatSessionService(db)
    items, total = session_svc.list_sessions(user_id=user_id, page=page, size=size)
    data = SessionListData(
        list=[
            SessionSummary(
                session_id=s.session_id,
                title=s.title,
                model=s.model,
                updated_at=_format_dt(s.updated_at),
                created_at=_format_dt(s.created_at),
            )
            for s in items
        ],
        total=total,
        page=page,
        size=size,
    )
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))


@router.get("/{session_id}/messages", response_model=Result)
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> Result:
    """获取某会话全部消息。游客持 session_id 可恢复；登录会话需本人。"""
    session_svc = ChatSessionService(db)
    session = session_svc.get_by_session_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not session_svc.can_access(session, user_id):
        raise HTTPException(status_code=403, detail="无权访问该会话")

    store = ChatMessageStore(db)
    raw = store.list_messages(session_id)
    messages = [
        ChatMessage(
            id=m.get("id"),
            role=m["role"],
            content=m["content"],
            created_at=m.get("created_at"),
            sources=m.get("sources"),
            ragEnabled=m.get("rag_enabled"),
        )
        for m in raw
    ]
    data = SessionMessagesData(
        session_id=session_id,
        title=session.title,
        messages=messages,
    )
    return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))


@router.put("/{session_id}", response_model=Result)
def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> Result:
    """修改会话标题（需登录且为本人会话）。"""
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")

    session_svc = ChatSessionService(db)
    try:
        session = session_svc.update_title(session_id, user_id, body.title)
        data = SessionSummary(
            session_id=session.session_id,
            title=session.title,
            model=session.model,
            updated_at=_format_dt(session.updated_at),
            created_at=_format_dt(session.created_at),
        )
        return Result(code=200, message="success", data=data, timestamp=int(time.time() * 1000))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{session_id}", response_model=Result)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> Result:
    """删除会话（需登录且为本人会话）。"""
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")

    session_svc = ChatSessionService(db)
    store = ChatMessageStore(db)
    try:
        session_svc.delete_session(session_id, user_id)
        store.clear_cache(session_id)
        return Result(code=200, message="success", data=None, timestamp=int(time.time() * 1000))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
