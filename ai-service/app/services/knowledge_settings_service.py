"""知识库访问权限配置。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import AiKnowledgeSettings


class KnowledgeSettingsService:
    SETTINGS_ID = 1

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_settings(self) -> AiKnowledgeSettings:
        record = (
            self.db.query(AiKnowledgeSettings)
            .filter(AiKnowledgeSettings.id == self.SETTINGS_ID)
            .one_or_none()
        )
        if record is None:
            record = AiKnowledgeSettings(
                id=self.SETTINGS_ID,
                guest_rag_enabled=0,
                user_rag_enabled=1,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        return record

    def update_settings(
        self,
        guest_rag_enabled: bool,
        user_rag_enabled: bool,
    ) -> AiKnowledgeSettings:
        record = self.get_settings()
        record.guest_rag_enabled = 1 if guest_rag_enabled else 0
        record.user_rag_enabled = 1 if user_rag_enabled else 0
        self.db.commit()
        self.db.refresh(record)
        return record

    def is_rag_allowed(self, user_id: Optional[int]) -> bool:
        settings = self.get_settings()
        if user_id is None:
            return bool(settings.guest_rag_enabled)
        return bool(settings.user_rag_enabled)

    def to_access_payload(self, user_id: Optional[int]) -> dict:
        settings = self.get_settings()
        guest_enabled = bool(settings.guest_rag_enabled)
        user_enabled = bool(settings.user_rag_enabled)
        current_allowed = user_enabled if user_id is not None else guest_enabled
        return {
            "guestRagEnabled": guest_enabled,
            "userRagEnabled": user_enabled,
            "currentUserAllowed": current_allowed,
            "currentUserType": "user" if user_id is not None else "guest",
            "updatedAt": settings.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            if settings.updated_at
            else None,
        }
