"""AI 对话与健康检查接口。"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_admin_context, get_optional_user_id
from app.db.session import get_db
from app.models.schemas import ChatRequest, ChatResponseData, ChatSource, Result
from app.services.agent_chat_service import AgentChatService
from app.services.blog_client import AdminContext
from app.services.rag_chat_service import RagChatService
from app.services.session_service import ChatSessionService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/ai", tags=["AI"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _use_agent_mode(request: ChatRequest) -> bool:
    if request.use_agent is not None:
        return request.use_agent
    return settings.chat_mode.lower() == "agent"


def _active_model(use_agent: bool) -> str:
    return settings.agent_model if use_agent else settings.tongyi_model


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
        "chat_mode": settings.chat_mode,
        "model": settings.tongyi_model,
        "agent_model": settings.agent_model,
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
    admin_ctx: AdminContext = Depends(get_admin_context),
) -> Result:
    """对话接口（同步，支持 Agent 或固定 RAG）。"""
    session_svc = ChatSessionService(db)
    use_agent = _use_agent_mode(request)
    try:
        session = session_svc.ensure_session(
            session_id=request.session_id,
            user_id=user_id,
            first_message=request.message,
        )
        if use_agent:
            chat_svc = AgentChatService(db, admin_ctx=admin_ctx)
        else:
            chat_svc = RagChatService(db)

        content, sources, rag_enabled, message_id = chat_svc.chat(
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
                model=_active_model(use_agent),
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
    admin_ctx: AdminContext = Depends(get_admin_context),
) -> StreamingResponse:
    """流式对话（SSE），支持 Agent 编排或固定 RAG。"""

    use_agent = _use_agent_mode(request)

    def event_generator():
        session_svc = ChatSessionService(db)
        if use_agent:
            chat_svc = AgentChatService(db, admin_ctx=admin_ctx)
        else:
            chat_svc = RagChatService(db)
        try:
            session = session_svc.ensure_session(
                session_id=request.session_id,
                user_id=user_id,
                first_message=request.message,
            )
            message_id: int | None = None
            rag_enabled = False

            for event_type, payload in chat_svc.stream_chat(
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
                    "model": _active_model(use_agent),
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
