"""会话记忆：从 ChatMessageStore 加载 + 本轮 ReAct 扩展。"""

from __future__ import annotations

from typing import Dict, List

from app.agent.models import Message, Role
from app.core.config import settings
from app.services.message_store import ChatMessageStore


class AgentSessionMemory:
    def __init__(self) -> None:
        self.messages: List[Message] = []

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def load_from_store(self, session_id: str, store: ChatMessageStore) -> None:
        raw = store.list_messages(session_id)
        window = settings.history_window
        if window > 0 and len(raw) > window:
            raw = raw[-window:]

        for item in raw:
            role = item.get("role")
            content = item.get("content") or ""
            if role == "user":
                self.messages.append(Message.user(content))
            elif role == "assistant":
                self.messages.append(Message.assistant(content))

    def get_openai_messages(self) -> List[Dict[str, str]]:
        return [msg.to_openai_format() for msg in self.messages]
