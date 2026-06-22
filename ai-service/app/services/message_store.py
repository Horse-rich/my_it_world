"""消息持久化与 Redis 热缓存（Redis 不可用时自动降级为仅 MySQL）。"""

import json
import logging
from datetime import datetime
from typing import List, Optional

import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_client import get_redis
from app.db.models import AiChatMessage, AiChatSession

logger = logging.getLogger(__name__)


def _history_key(session_id: str) -> str:
    return f"ai:chat:history:{session_id}"


def _session_ttl(session: Optional[AiChatSession]) -> int:
    if session and session.user_id is not None:
        ttl = settings.user_session_ttl_seconds
        return ttl if ttl > 0 else 0
    return settings.guest_session_ttl_seconds


class ChatMessageStore:
    """MySQL 持久化 + Redis 热缓存。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._redis: Optional[redis.Redis] = None
        try:
            self._redis = get_redis()
        except redis.RedisError as e:
            logger.warning("Redis 初始化失败，将仅使用 MySQL: %s", e)

    def list_messages(self, session_id: str) -> List[dict]:
        cached = self._redis_get(_history_key(session_id))
        if cached:
            return json.loads(cached)

        rows = (
            self._db.query(AiChatMessage)
            .filter(AiChatMessage.session_id == session_id)
            .order_by(AiChatMessage.created_at.asc(), AiChatMessage.id.asc())
            .all()
        )
        messages = [self._row_to_dict(row) for row in rows]
        if messages:
            self._write_cache(session_id, messages)
        return messages

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        session: Optional[AiChatSession] = None,
        sources_json: Optional[dict] = None,
    ) -> AiChatMessage:
        row = AiChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources_json=sources_json,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)

        rows = (
            self._db.query(AiChatMessage)
            .filter(AiChatMessage.session_id == session_id)
            .order_by(AiChatMessage.created_at.asc(), AiChatMessage.id.asc())
            .all()
        )
        messages = [self._row_to_dict(r) for r in rows]
        self._write_cache(session_id, messages, session)

        return row

    def clear_cache(self, session_id: str) -> None:
        self._redis_delete(_history_key(session_id))

    def _write_cache(
        self,
        session_id: str,
        messages: List[dict],
        session: Optional[AiChatSession] = None,
    ) -> None:
        key = _history_key(session_id)
        ttl = _session_ttl(session)
        payload = json.dumps(messages, ensure_ascii=False)
        if ttl > 0:
            self._redis_setex(key, ttl, payload)
        else:
            self._redis_set(key, payload)

    def _redis_get(self, key: str) -> Optional[str]:
        if not self._redis:
            return None
        try:
            return self._redis.get(key)
        except redis.RedisError as e:
            logger.warning("Redis GET 失败，降级 MySQL: %s", e)
            return None

    def _redis_set(self, key: str, value: str) -> None:
        if not self._redis:
            return
        try:
            self._redis.set(key, value)
        except redis.RedisError as e:
            logger.warning("Redis SET 失败: %s", e)

    def _redis_setex(self, key: str, ttl: int, value: str) -> None:
        if not self._redis:
            return
        try:
            self._redis.setex(key, ttl, value)
        except redis.RedisError as e:
            logger.warning("Redis SETEX 失败: %s", e)

    def _redis_delete(self, key: str) -> None:
        if not self._redis:
            return
        try:
            self._redis.delete(key)
        except redis.RedisError as e:
            logger.warning("Redis DELETE 失败: %s", e)

    def _row_to_dict(self, row: AiChatMessage) -> dict:
        created = row.created_at
        if isinstance(created, datetime):
            created_str = created.isoformat()
        else:
            created_str = str(created)
        item = {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "created_at": created_str,
        }
        if row.sources_json:
            sources = row.sources_json.get("sources")
            if sources is not None:
                item["sources"] = sources
            if "ragEnabled" in row.sources_json:
                item["rag_enabled"] = bool(row.sources_json.get("ragEnabled"))
        return item
