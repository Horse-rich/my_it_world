"""ReAct Agent 运行时（无 CLI 依赖，支持事件回调 / 生成器）。"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from app.agent.config import AgentRuntimeConfig
from app.agent.llm_client import AgentLLMClient
from app.agent.memory.session_memory import AgentSessionMemory
from app.agent.models import AgentStep, Message, Role, ToolCall, ToolCallStatus, ToolResult
from app.agent.tools.base import BaseTool, tool_schemas

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, dict], None]


class ReActAgent:
    """推理 + 行动循环，按需调用工具直至产出最终回答。"""

    def __init__(
        self,
        llm: AgentLLMClient,
        memory: AgentSessionMemory,
        tools: List[BaseTool],
        config: AgentRuntimeConfig,
        on_event: Optional[EventCallback] = None,
    ) -> None:
        self.llm = llm
        self.memory = memory
        self.config = config
        self.on_event = on_event
        self.tools_map: Dict[str, BaseTool] = {t.name: t for t in tools}
        self.tool_schemas = tool_schemas(tools)
        self.steps: List[AgentStep] = []

    def _emit(self, event_type: str, payload: dict) -> None:
        if self.on_event:
            self.on_event(event_type, payload)

    def run_events(self) -> Generator[Tuple[str, dict], None, None]:
        """执行 ReAct 循环，yield SSE 风格事件；最后 yield ('final', {'content': ...})。"""
        self.steps = []
        final_answer: Optional[str] = None

        for step_num in range(self.config.max_steps):
            step = self._execute_step(step_num + 1)
            self.steps.append(step)

            if step.thought:
                payload = {"step": step.step_number, "thought": step.thought[:500]}
                self._emit("agent_step", payload)
                yield "agent_step", payload

            for tc in step.tool_calls:
                call_payload = {
                    "name": tc.tool_name,
                    "args": tc.tool_args,
                }
                self._emit("tool_call", call_payload)
                yield "tool_call", call_payload

            for result in step.results:
                result_payload = {
                    "name": result.tool_name,
                    "preview": result.content[:300],
                    "status": result.status.value,
                }
                self._emit("tool_result", result_payload)
                yield "tool_result", result_payload

            if step.final_answer:
                final_answer = step.final_answer
                break

        if not final_answer:
            final_answer = "抱歉，我尝试了多次但仍无法完整回答这个问题，请换个方式提问。"

        final_payload = {"content": final_answer}
        self._emit("final", final_payload)
        yield "final", final_payload

    def _execute_step(self, step_number: int) -> AgentStep:
        step = AgentStep(step_number=step_number)
        messages = self.memory.get_openai_messages()

        response = self.llm.chat(messages, tools=self.tool_schemas or None)
        thought = (response.get("content") or "").strip()
        step.thought = thought

        raw_tool_calls = response.get("tool_calls")
        if raw_tool_calls:
            parsed_calls = self.llm.parse_tool_calls(raw_tool_calls)
            step.tool_calls = parsed_calls

            if self._is_duplicate_tool_request(parsed_calls):
                last_content = self._get_last_tool_result_content(parsed_calls[0].tool_name)
                step.final_answer = (
                    f"根据工具查询结果：{last_content}"
                    if last_content
                    else thought or "工具已返回结果，请参考上述信息。"
                )
                return step

            assistant_msg = Message.assistant(thought, tool_calls=parsed_calls)
            self.memory.add_message(assistant_msg)

            results = self._execute_tool_calls(parsed_calls)
            step.results = results

            for result in results:
                self.memory.add_message(
                    Message.tool_result(
                        call_id=result.call_id,
                        tool_name=result.tool_name,
                        content=result.content,
                    )
                )
        else:
            step.final_answer = thought

        return step

    def _tool_call_signature(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        return f"{tool_name}:{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"

    def _is_duplicate_tool_request(self, tool_calls: List[ToolCall]) -> bool:
        seen: set[str] = set()
        for msg in self.memory.messages:
            if msg.role != Role.ASSISTANT or not msg.tool_calls:
                continue
            for tc in msg.tool_calls:
                seen.add(self._tool_call_signature(tc.tool_name, tc.tool_args))

        return any(
            self._tool_call_signature(tc.tool_name, tc.tool_args) in seen for tc in tool_calls
        )

    def _get_last_tool_result_content(self, tool_name: str) -> str:
        for msg in reversed(self.memory.messages):
            if msg.role == Role.TOOL and msg.metadata.get("tool_name") == tool_name:
                return msg.content
        return ""

    def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        results: List[ToolResult] = []
        for tc in tool_calls:
            tool = self.tools_map.get(tc.tool_name)
            if not tool:
                results.append(
                    ToolResult(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        content=f"未找到工具: {tc.tool_name}",
                        status=ToolCallStatus.ERROR,
                        error=f"Unknown tool: {tc.tool_name}",
                    )
                )
                continue

            try:
                output = tool.execute(**tc.tool_args)
                results.append(
                    ToolResult(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        content=output,
                        status=ToolCallStatus.SUCCESS,
                    )
                )
            except Exception as e:
                logger.exception("工具 %s 执行失败", tc.tool_name)
                results.append(
                    ToolResult(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        content=f"工具执行出错: {e}",
                        status=ToolCallStatus.ERROR,
                        error=str(e),
                    )
                )
        return results
