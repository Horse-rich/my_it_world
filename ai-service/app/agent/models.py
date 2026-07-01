"""Agent 核心数据结构。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ToolCall:
    tool_name: str
    tool_args: Dict[str, Any]
    call_id: str = field(default="", init=False)

    def __post_init__(self) -> None:
        import uuid

        if not self.call_id:
            self.call_id = f"call_{uuid.uuid4().hex[:8]}"

    def to_api_format(self) -> Dict[str, Any]:
        return {
            "id": self.call_id,
            "type": "function",
            "function": {
                "name": self.tool_name,
                "arguments": json.dumps(self.tool_args, ensure_ascii=False),
            },
        }


@dataclass
class ToolResult:
    call_id: str
    tool_name: str
    content: str
    status: ToolCallStatus = ToolCallStatus.SUCCESS
    error: Optional[str] = None


@dataclass
class Message:
    role: Role
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_openai_format(self) -> Dict[str, Any]:
        if self.role == Role.ASSISTANT and self.tool_calls:
            return {
                "role": self.role.value,
                "content": self.content or None,
                "tool_calls": [tc.to_api_format() for tc in self.tool_calls],
            }

        msg: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.role == Role.TOOL and self.metadata.get("tool_name"):
            msg["name"] = self.metadata["tool_name"]
        return msg

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(Role.SYSTEM, content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(Role.USER, content)

    @classmethod
    def assistant(
        cls, content: str, tool_calls: Optional[List[ToolCall]] = None
    ) -> Message:
        return cls(Role.ASSISTANT, content, tool_calls=tool_calls)

    @classmethod
    def tool_result(cls, call_id: str, tool_name: str, content: str) -> Message:
        return cls(
            Role.TOOL,
            content,
            tool_call_id=call_id,
            metadata={"tool_name": tool_name},
        )


@dataclass
class AgentStep:
    step_number: int
    thought: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    results: List[ToolResult] = field(default_factory=list)
    final_answer: Optional[str] = None
