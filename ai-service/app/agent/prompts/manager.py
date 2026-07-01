"""Agent Prompt 模板。"""

from __future__ import annotations

from typing import Any, Dict, Optional


class PromptManager:
    def __init__(self) -> None:
        self._templates: Dict[str, str] = {}
        self._register_defaults()

    def render(self, name: str, **kwargs: Any) -> Optional[str]:
        tmpl = self._templates.get(name)
        if not tmpl:
            return None
        result = tmpl
        for key, value in kwargs.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    def _register_defaults(self) -> None:
        self._templates["site_assistant_system"] = """\
你是 My IT World 个人网站上的 AI 助手，擅长编程、云计算、Java、Spring、前端等技术问题。

## 能力
- 可使用工具检索本站**已入库的全部博客**（含技术文、个人介绍、站点说明等）
- 查询人物/主题时必须先调用 search_blog_chunks，再根据工具返回回答；不要臆测「检索为空」
- 优先基于工具返回的站内资料回答，并注明信息来源
- 若工具明确返回 [RAG_DISABLED] / [RAG_EMPTY]，再说明原因；否则不得声称「知识库没有」

## 工作流程 (ReAct)
1. 思考用户问题需要什么信息
2. 涉及站内内容时调用 search_blog_chunks（query 用用户关心的关键词）
3. 根据工具结果组织简洁、准确的中文回答
4. 不要重复调用相同工具与相同参数

## 可用工具
{tool_descriptions}

回答请简洁清晰，使用中文。"""
