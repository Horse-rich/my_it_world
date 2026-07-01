"""Agent 编排：会话记忆 + ReAct + SSE 事件流。"""

from __future__ import annotations

import logging
from typing import Generator, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.agent.memory.session_memory import AgentSessionMemory
from app.agent.models import Message
from app.agent.profiles.site_assistant import build_site_assistant_agent
from app.agent.tools.context import ToolContext
from app.db.models import AiChatSession
from app.services.blog_client import AdminContext
from app.services.knowledge_settings_service import KnowledgeSettingsService
from app.services.message_store import ChatMessageStore
from app.services.session_service import ChatSessionService

logger = logging.getLogger(__name__)

_TOKEN_CHUNK = 24


class AgentOrchestrator:
    def __init__(self, db: Session, admin_ctx: Optional[AdminContext] = None) -> None:
        self.db = db
        self.admin_ctx = admin_ctx
        self.message_store = ChatMessageStore(db)
        self.session_svc = ChatSessionService(db)
        self.settings_svc = KnowledgeSettingsService(db)

    def _sources_payload(
        self,
        sources: List[dict],
        rag_enabled: bool,
    ) -> Optional[dict]:
        if not rag_enabled and not sources:
            return None
        return {"sources": sources, "ragEnabled": rag_enabled}

    def run_stream(
        self,
        session: AiChatSession,
        message: str,
        user_id: Optional[int],
    ) -> Generator[Tuple[str, dict], None, None]:
        """流式 Agent 对话，yield SSE 事件元组。"""
        rag_enabled = self.settings_svc.is_rag_allowed(user_id)
        ctx = ToolContext(
            db=self.db,
            user_id=user_id,
            admin_ctx=self.admin_ctx,
        )

        memory = AgentSessionMemory()
        memory.load_from_store(session.session_id, self.message_store)
        self.message_store.append_message(
            session.session_id,
            "user",
            message,
            session,
        )
        memory.add_message(Message.user(message))

        sources_emitted = False
        agent = build_site_assistant_agent(ctx, memory)

        final_content = ""
        for event_type, payload in agent.run_events():
            if event_type == "final":
                final_content = payload.get("content", "")
                continue

            yield event_type, payload

            if (
                event_type == "tool_result"
                and payload.get("name") == "search_blog_chunks"
                and ctx.collected_sources
            ):
                yield "source", {
                    "sources": list(ctx.collected_sources),
                    "ragEnabled": rag_enabled,
                }
                sources_emitted = True

        if ctx.collected_sources and not sources_emitted:
            yield "source", {
                "sources": list(ctx.collected_sources),
                "ragEnabled": rag_enabled,
            }
        elif rag_enabled and not sources_emitted:
            yield "source", {"sources": [], "ragEnabled": True}

        for i in range(0, len(final_content), _TOKEN_CHUNK):
            yield "token", {"content": final_content[i:i + _TOKEN_CHUNK]}

        assistant_row = self.message_store.append_message(
            session.session_id,
            "assistant",
            final_content.strip(),
            session,
            sources_json=self._sources_payload(ctx.collected_sources, rag_enabled),
        )
        self.session_svc.touch_session(session.session_id)

        yield "done", {
            "messageId": assistant_row.id,
            "ragEnabled": rag_enabled,
        }

    def run_sync(
        self,
        session: AiChatSession,
        message: str,
        user_id: Optional[int],
    ) -> Tuple[str, List[dict], bool, int]:
        """同步 Agent 对话，返回 (content, sources, rag_enabled, message_id)。"""
        content = ""
        sources: List[dict] = []
        rag_enabled = False
        message_id = 0

        for event_type, payload in self.run_stream(session, message, user_id):
            if event_type == "token":
                content += payload.get("content", "")
            elif event_type == "source":
                sources = payload.get("sources") or []
                rag_enabled = bool(payload.get("ragEnabled"))
            elif event_type == "done":
                message_id = int(payload.get("messageId") or 0)

        return content.strip(), sources, rag_enabled, message_id
