"""AI 对话与健康检查接口。"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_optional_user_id
from app.db.session import get_db
from app.models.schemas import ChatRequest, ChatResponseData, ChatSource, Result
from app.services.rag_chat_service import RagChatService
from app.services.session_service import ChatSessionService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/ai", tags=["AI"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/health")
def health() -> dict:
    """健康检查（无需 API Key）。"""
    qdrant_ok = False
    try:
        store = get_vector_store()
        store.ensure_collection()
        qdrant_ok = True
    except Exception:
        pass
    return {
        "status": "ok",
        "service": "ai-service",
        "model": settings.tongyi_model,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "ollama_base_url": settings.ollama_base_url
        if settings.embedding_provider.lower() == "ollama"
        else None,
        "qdrant_url": settings.qdrant_url,
        "qdrant_ok": qdrant_ok,
        "api_key_configured": bool(settings.dashscope_api_key),
    }


@router.post("/chat", response_model=Result)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> Result:
    """对话接口（同步，含 RAG）。"""
    session_svc = ChatSessionService(db)
    rag_chat = RagChatService(db)
    try:
        session = session_svc.ensure_session(
            session_id=request.session_id,
            user_id=user_id,
            first_message=request.message,
        )
        content, sources, rag_enabled, message_id = rag_chat.chat(
            session=session,
            message=request.message,
            user_id=user_id,
        )

        source_models = [ChatSource(**item) for item in sources] if sources else None
        return Result(
            code=200,
            message="success",
            data=ChatResponseData(
                content=content,
                session_id=session.session_id,
                model=settings.tongyi_model,
                message_id=message_id,
                sources=source_models,
                ragEnabled=rag_enabled,
            ),
            timestamp=int(time.time() * 1000),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {e}") from e


@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int | None = Depends(get_optional_user_id),
) -> StreamingResponse:
    """流式对话（SSE），含 RAG 引用来源事件。"""

    def event_generator():
        session_svc = ChatSessionService(db)
        rag_chat = RagChatService(db)
        try:
            session = session_svc.ensure_session(
                session_id=request.session_id,
                user_id=user_id,
                first_message=request.message,
            )
            message_id: int | None = None
            rag_enabled = False

            for event_type, payload in rag_chat.stream_chat(
                session=session,
                message=request.message,
                user_id=user_id,
            ):
                if event_type == "done":
                    message_id = payload.get("messageId")
                    rag_enabled = bool(payload.get("ragEnabled"))
                    continue
                yield _sse_event(event_type, payload)

            yield _sse_event(
                "done",
                {
                    "sessionId": session.session_id,
                    "model": settings.tongyi_model,
                    "messageId": message_id,
                    "ragEnabled": rag_enabled,
                },
            )
        except PermissionError as e:
            yield _sse_event("error", {"message": str(e), "code": 403})
        except Exception as e:
            yield _sse_event("error", {"message": f"AI 调用失败: {e}", "code": 500})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
