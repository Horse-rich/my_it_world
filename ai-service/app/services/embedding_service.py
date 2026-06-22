"""Embedding 向量化：支持 Ollama（本地/远程）与百炼 DashScope。"""

from __future__ import annotations

import os
from typing import List

import httpx

from app.core.config import settings

# DashScope 单次 batch 上限
_DASHSCOPE_BATCH_SIZE = 25
# Ollama 单次 batch（可按机器性能调整）
_OLLAMA_BATCH_SIZE = 32


def embed_texts(texts: List[str]) -> List[List[float]]:
    """批量文本 → 向量列表，入库时使用。"""
    if not texts:
        return []

    provider = settings.embedding_provider.lower()
    if provider == "ollama":
        vectors = _embed_ollama(texts)
    elif provider == "dashscope":
        vectors = _embed_dashscope(texts)
    else:
        raise ValueError(f"不支持的 EMBEDDING_PROVIDER: {settings.embedding_provider}")

    _validate_vectors(vectors, len(texts))
    return vectors


def embed_query(text: str) -> List[float]:
    """单条查询文本 → 向量，检索时使用。"""
    return embed_texts([text])[0]


def _validate_vectors(vectors: List[List[float]], expected_count: int) -> None:
    if len(vectors) != expected_count:
        raise RuntimeError(
            f"Embedding 数量不匹配: 期望 {expected_count}，实际 {len(vectors)}"
        )
    if not vectors:
        return
    dim = len(vectors[0])
    if dim != settings.embedding_dimension:
        raise RuntimeError(
            f"Embedding 维度不匹配: 配置 EMBEDDING_DIMENSION={settings.embedding_dimension}，"
            f"实际模型输出 {dim}。请修正 .env 或更换 Qdrant collection 后重新入库。"
        )


def _embed_ollama(texts: List[str]) -> List[List[float]]:
    """调用 Ollama /api/embed（如 qwen3-embedding:0.6b）。"""
    base = settings.ollama_base_url.rstrip("/")
    url = f"{base}/api/embed"
    all_vectors: List[List[float]] = []

    with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
        for start in range(0, len(texts), _OLLAMA_BATCH_SIZE):
            batch = texts[start : start + _OLLAMA_BATCH_SIZE]
            response = client.post(
                url,
                json={"model": settings.embedding_model, "input": batch},
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama Embedding 失败: HTTP {response.status_code} {response.text}"
                )
            data = response.json()
            embeddings = data.get("embeddings") or []
            if len(embeddings) != len(batch):
                raise RuntimeError(
                    f"Ollama 返回向量数不匹配: 期望 {len(batch)}，实际 {len(embeddings)}"
                )
            all_vectors.extend(embeddings)

    return all_vectors


def _embed_dashscope(texts: List[str]) -> List[List[float]]:
    """调用百炼 text-embedding-v3。"""
    import dashscope
    from dashscope import TextEmbedding

    if not settings.dashscope_api_key:
        raise ValueError("未配置 DASHSCOPE_API_KEY")
    os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
    dashscope.api_key = settings.dashscope_api_key

    all_vectors: List[List[float]] = []
    for start in range(0, len(texts), _DASHSCOPE_BATCH_SIZE):
        batch = texts[start : start + _DASHSCOPE_BATCH_SIZE]
        response = TextEmbedding.call(
            model=settings.embedding_model,
            input=batch,
            dimension=settings.embedding_dimension,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope Embedding 失败: {response.code} {response.message}"
            )
        embeddings = response.output.get("embeddings") or []
        embeddings.sort(key=lambda item: item.get("text_index", 0))
        for item in embeddings:
            all_vectors.append(item["embedding"])

    return all_vectors
