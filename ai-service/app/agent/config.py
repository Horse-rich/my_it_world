"""Agent 运行时配置。"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class AgentRuntimeConfig:
    model: str = "qwen-plus"
    temperature: float = 0.7
    max_tokens: int = 2048
    max_steps: int = 6
    verbose_log: bool = False

    @classmethod
    def from_settings(cls) -> AgentRuntimeConfig:
        return cls(
            model=settings.agent_model,
            max_steps=settings.agent_max_steps,
            verbose_log=settings.agent_verbose_log,
        )
