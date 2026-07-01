"""工具基类。"""

from __future__ import annotations

import abc
from typing import Any, ClassVar, Dict, List


class BaseTool(abc.ABC):
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    parameters: ClassVar[Dict[str, Any]] = {}

    @abc.abstractmethod
    def execute(self, **kwargs) -> str:
        ...

    def to_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [
                        k
                        for k, v in self.parameters.items()
                        if v.get("required", False)
                    ],
                },
            },
        }


def tool_schemas(tools: List[BaseTool]) -> List[Dict[str, Any]]:
    return [tool.to_schema() for tool in tools]
