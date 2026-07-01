"""工具运行时上下文（每次对话注入）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.services.blog_client import AdminContext


@dataclass
class ToolContext:
    db: Session
    user_id: Optional[int]
    admin_ctx: Optional[AdminContext] = None
    collected_sources: List[dict] = field(default_factory=list)
