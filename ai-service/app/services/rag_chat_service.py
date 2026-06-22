"""RAG 增强对话编排：检索 → Prompt → LLM（同步/流式）。"""

from __future__ import annotations

import logging
from typing import Generator, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AiChatSession
from app.services.llm_service import get_llm
from app.services.message_store import ChatMessageStore
from app.services.rag_service import RagService
from app.services.session_service import ChatSessionService

logger = logging.getLogger(__name__)


def _window_messages(messages: List[dict]) -> List[dict]:
    window = settings.history_window
    if window <= 0 or len(messages) <= window:
        return messages
    return messages[-window:]


def _to_langchain_messages(messages: List[dict]) -> List[BaseMessage]:
    result: List[BaseMessage] = []
    for item in messages:
        role = item["role"]
        content = item["content"]
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result


class RagChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rag = RagService(db)
        self.message_store = ChatMessageStore(db)
        self.session_svc = ChatSessionService(db)

    def retrieve_for_query(
        self,
        user_id: Optional[int],
        query: str,
    ) -> Tuple[List[dict], Optional[str], bool]:
        _, sources, context, rag_enabled = self.rag.retrieve(user_id, query)
        return sources, context, rag_enabled

    def _build_llm_messages(
        self,
        session_id: str,
        rag_context: Optional[str],
    ) -> List[BaseMessage]:
        raw = self.message_store.list_messages(session_id)
        windowed = _window_messages(raw)
        system = settings.system_prompt
        if rag_context:
            system = f"{system}\n\n{rag_context}"
        return [SystemMessage(content=system), *_to_langchain_messages(windowed)]

    def _sources_payload(
        self,
        sources: List[dict],
        rag_enabled: bool,
    ) -> Optional[dict]:
        if not rag_enabled and not sources:
            return None
        return {"sources": sources, "ragEnabled": rag_enabled}

    def chat(
        self,
        session: AiChatSession,
        message: str,
        user_id: Optional[int],
    ) -> Tuple[str, List[dict], bool, int]:
        """
        同步 RAG 对话。
        返回 (content, sources, rag_enabled, assistant_message_id)。
        """
        sources, rag_context, rag_enabled = self.retrieve_for_query(user_id, message)

        self.message_store.append_message(
            session.session_id,
            "user",
            message,
            session,
        )

        llm_messages = self._build_llm_messages(session.session_id, rag_context)
        response = get_llm(streaming=False).invoke(llm_messages)
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()

        assistant_row = self.message_store.append_message(
            session.session_id,
            "assistant",
            content,
            session,
            sources_json=self._sources_payload(sources, rag_enabled),
        )
        self.session_svc.touch_session(session.session_id)
        return content, sources, rag_enabled, assistant_row.id

    def stream_chat(
        self,
        session: AiChatSession,
        message: str,
        user_id: Optional[int],
    ) -> Generator[Tuple[str, dict], None, None]:
        """
        流式 RAG 对话。
        依次 yield: ("source", {...}), ("token", {"content": "..."}), 最后由调用方发 done。
        """
        sources, rag_context, rag_enabled = self.retrieve_for_query(user_id, message)

        self.message_store.append_message(
            session.session_id,
            "user",
            message,
            session,
        )

        if sources:
            yield "source", {"sources": sources, "ragEnabled": rag_enabled}
        elif rag_enabled:
            yield "source", {"sources": [], "ragEnabled": True}

        llm_messages = self._build_llm_messages(session.session_id, rag_context)
        full_content = ""
        for chunk in get_llm(streaming=True).stream(llm_messages):
            piece = chunk.content if hasattr(chunk, "content") else str(chunk)
            if not piece:
                continue
            full_content += piece
            yield "token", {"content": piece}

        assistant_row = self.message_store.append_message(
            session.session_id,
            "assistant",
            full_content.strip(),
            session,
            sources_json=self._sources_payload(sources, rag_enabled),
        )
        self.session_svc.touch_session(session.session_id)
        yield "done", {
            "messageId": assistant_row.id,
            "ragEnabled": rag_enabled,
        }
