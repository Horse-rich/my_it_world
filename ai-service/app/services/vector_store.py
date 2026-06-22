"""Qdrant 向量库封装。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.services.chunk_service import TextChunk

_vector_store: Optional["VectorStore"] = None

ScoredItem = Union[qmodels.ScoredPoint, Dict[str, Any]]


@dataclass
class SearchHit:
    score: float
    blog_id: int
    title: str
    chunk_index: int
    source_url: str
    text: str
    publish_time: Optional[str] = None


class VectorStore:
    def __init__(self) -> None:
        try:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                check_compatibility=False,
            )
        except TypeError:
            # 旧版 qdrant-client 无 check_compatibility 参数
            self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )

    def delete_by_blog_id(self, blog_id: int) -> None:
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="blog_id",
                            match=qmodels.MatchValue(value=blog_id),
                        )
                    ]
                )
            ),
        )

    def upsert_chunks(
        self,
        blog_id: int,
        title: str,
        source_url: str,
        publish_time: Optional[str],
        chunks: List[TextChunk],
        vectors: List[List[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")

        self.ensure_collection()
        points: List[qmodels.PointStruct] = []
        for chunk, vector in zip(chunks, vectors):
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"blog:{blog_id}:chunk:{chunk.chunk_index}",
                )
            )
            payload: Dict[str, Any] = {
                "blog_id": blog_id,
                "title": title,
                "chunk_index": chunk.chunk_index,
                "source_url": source_url,
                "text": chunk.text,
                "publish_time": publish_time,
            }
            points.append(
                qmodels.PointStruct(id=point_id, vector=vector, payload=payload)
            )

        batch_size = 64
        for start in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection,
                points=points[start : start + batch_size],
            )

    def search(
        self,
        query_vector: List[float],
        top_k: Optional[int] = None,
        blog_id: Optional[int] = None,
    ) -> List[SearchHit]:
        self.ensure_collection()
        limit = top_k or settings.search_top_k

        query_filter = None
        if blog_id is not None:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="blog_id",
                        match=qmodels.MatchValue(value=blog_id),
                    )
                ]
            )

        results = self._query_vectors(query_vector, limit, query_filter)
        return self._to_search_hits(results)

    def _query_vectors(
        self,
        query_vector: List[float],
        limit: int,
        query_filter: Optional[qmodels.Filter],
    ) -> List[ScoredItem]:
        """
        兼容 Qdrant Server 1.9.x 与 qdrant-client 各版本：
        - 1.9~1.15 client：优先 client.search()
        - 1.16+ client（无 search）：直接 REST /points/search（兼容 1.9.x server）
        """
        if hasattr(self.client, "search"):
            try:
                return self.client.search(
                    collection_name=self.collection,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                )
            except Exception as exc:
                if not self._is_not_found_error(exc):
                    raise

        return self._search_via_http(query_vector, limit, query_filter)

    def _search_via_http(
        self,
        query_vector: List[float],
        limit: int,
        query_filter: Optional[qmodels.Filter],
    ) -> List[Dict[str, Any]]:
        """直接调用 Qdrant 1.9.x 支持的 /points/search REST 接口。"""
        url = (
            f"{settings.qdrant_url.rstrip('/')}/collections/"
            f"{self.collection}/points/search"
        )
        body: Dict[str, Any] = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
        }
        if query_filter is not None:
            body["filter"] = query_filter.model_dump(exclude_none=True)

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=body)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Qdrant REST search 失败: HTTP {response.status_code} {response.text}"
                )
            data = response.json()
        return data.get("result") or []

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        text = str(exc)
        return "404" in text or "Not Found" in text

    @staticmethod
    def _to_search_hits(results: List[ScoredItem]) -> List[SearchHit]:
        hits: List[SearchHit] = []
        for item in results:
            if isinstance(item, dict):
                payload = item.get("payload") or {}
                score = float(item.get("score", 0))
            else:
                payload = item.payload or {}
                score = float(item.score)
            hits.append(
                SearchHit(
                    score=score,
                    blog_id=int(payload.get("blog_id", 0)),
                    title=str(payload.get("title") or ""),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    source_url=str(payload.get("source_url") or ""),
                    text=str(payload.get("text") or ""),
                    publish_time=payload.get("publish_time"),
                )
            )
        return hits

    def count_points(self) -> int:
        if not self.client.collection_exists(self.collection):
            return 0
        info = self.client.get_collection(self.collection)
        return int(info.points_count or 0)


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
