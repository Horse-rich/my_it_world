"""site-assistant Profile：工具集 + 系统 Prompt。"""

from __future__ import annotations

from app.agent.config import AgentRuntimeConfig
from app.agent.llm_client import AgentLLMClient
from app.agent.memory.session_memory import AgentSessionMemory
from app.agent.models import Message, Role
from app.agent.prompts.manager import PromptManager
from app.agent.runtime.react_agent import ReActAgent
from app.agent.tools.context import ToolContext
from app.agent.tools.site_tools import build_site_assistant_tools


def build_site_assistant_agent(
    ctx: ToolContext,
    memory: AgentSessionMemory,
    config: AgentRuntimeConfig | None = None,
    on_event=None,
) -> ReActAgent:
    runtime = config or AgentRuntimeConfig.from_settings()
    tools = build_site_assistant_tools(ctx)

    tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    prompt_mgr = PromptManager()
    system = prompt_mgr.render(
        "site_assistant_system",
        tool_descriptions=tool_descriptions,
    ) or "你是 My IT World 网站 AI 助手。"

    if not any(m.role == Role.SYSTEM for m in memory.messages):
        memory.add_message(Message.system(system))

    llm = AgentLLMClient(
        model=runtime.model,
        temperature=runtime.temperature,
        max_tokens=runtime.max_tokens,
    )
    return ReActAgent(
        llm=llm,
        memory=memory,
        tools=tools,
        config=runtime,
        on_event=on_event,
    )
