"""Agent 模式对话服务（对外与 RagChatService 同形接口）。"""

from __future__ import annotations

from typing import Generator, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.db.models import AiChatSession
from app.services.blog_client import AdminContext


class AgentChatService:
    def __init__(
        self,
        db: Session,
        admin_ctx: Optional[AdminContext] = None,
    ) -> None:
        self._orchestrator = AgentOrchestrator(db, admin_ctx=admin_ctx)

    def chat(
        self,
        session: AiChatSession,
        message: str,
        user_id: Optional[int],
    ) -> Tuple[str, List[dict], bool, int]:
        return self._orchestrator.run_sync(session, message, user_id)

    def stream_chat(
        self,
        session: AiChatSession,
        message: str,
        user_id: Optional[int],
    ) -> Generator[Tuple[str, dict], None, None]:
        return self._orchestrator.run_stream(session, message, user_id)
