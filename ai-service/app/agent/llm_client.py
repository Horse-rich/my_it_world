"""DashScope LLM 客户端（Function Calling）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from app.agent.models import ToolCall
from app.core.config import settings

logger = logging.getLogger(__name__)


def _read_output_field(output: Any, name: str, default: Any = None) -> Any:
    """安全读取 DashScope output 字段（缺失时可能 KeyError，而非 AttributeError）。"""
    if output is None:
        return default
    if isinstance(output, dict):
        return output.get(name, default)
    try:
        value = getattr(output, name, default)
        return value if value is not None else default
    except KeyError:
        return default


class AgentLLMClient:
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 2048) -> None:
        if not settings.dashscope_api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")
        os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._total_tokens = 0

        import dashscope
        from dashscope import Generation

        dashscope.api_key = settings.dashscope_api_key
        self._Generation = Generation

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "incremental_output": False,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = self._Generation.call(**params)
        if response.status_code != 200:
            raise RuntimeError(f"DashScope API error: {response.code} - {response.message}")

        output = response.output
        choices = _read_output_field(output, "choices", []) or []
        if not choices:
            return {"content": "", "tool_calls": None, "finish_reason": "stop"}

        choice = choices[0]
        if isinstance(choice, dict):
            message = choice.get("message", {}) or {}
            content = message.get("content", "") or ""
            raw_tool_calls = message.get("tool_calls", []) or []
            finish_reason = choice.get("finish_reason", "stop")
        else:
            message = _read_output_field(choice, "message", {}) or {}
            if isinstance(message, dict):
                content = message.get("content", "") or ""
                raw_tool_calls = message.get("tool_calls", []) or []
            else:
                content = _read_output_field(message, "content", "") or ""
                raw_tool_calls = _read_output_field(message, "tool_calls", []) or []
            finish_reason = _read_output_field(choice, "finish_reason", "stop")

        usage = _read_output_field(output, "usage")
        if usage is not None:
            if isinstance(usage, dict):
                total = usage.get("total_tokens", 0)
            else:
                total = getattr(usage, "total_tokens", 0)
            if total:
                self._total_tokens += total

        tool_calls = [_DashScopeToolCall(block) for block in raw_tool_calls]
        return {
            "content": content,
            "tool_calls": tool_calls if tool_calls else None,
            "finish_reason": finish_reason,
        }

    def parse_tool_calls(self, raw_tool_calls: Any) -> List[ToolCall]:
        tool_calls: List[ToolCall] = []
        if not raw_tool_calls:
            return tool_calls

        for tc in raw_tool_calls:
            func = getattr(tc, "function", None) or {}
            name = func.get("name", "") if isinstance(func, dict) else getattr(func, "name", "")
            args_str = (
                func.get("arguments", "{}")
                if isinstance(func, dict)
                else getattr(func, "arguments", "{}")
            )
            call_id = getattr(tc, "id", "") or str(getattr(tc, "index", 0))
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}
            tool_call = ToolCall(tool_name=name, tool_args=args)
            tool_call.call_id = str(call_id)
            tool_calls.append(tool_call)
        return tool_calls

    @property
    def total_tokens(self) -> int:
        return self._total_tokens


class _DashScopeToolCall:
    def __init__(self, block: Any) -> None:
        if isinstance(block, dict):
            func_data = block.get("function", {}) or {}
            call_id = block.get("id", str(block.get("index", 0)))
        else:
            func_data = _read_output_field(block, "function", {}) or {}
            call_id = _read_output_field(block, "id", None) or str(
                _read_output_field(block, "index", 0)
            )
        if isinstance(func_data, dict):
            name = func_data.get("name", "")
            arguments = func_data.get("arguments", "{}")
        else:
            name = _read_output_field(func_data, "name", "")
            arguments = _read_output_field(func_data, "arguments", "{}")
        self.id = call_id
        self.function = type(
            "_Func",
            (),
            {
                "name": name,
                "arguments": arguments,
            },
        )()
