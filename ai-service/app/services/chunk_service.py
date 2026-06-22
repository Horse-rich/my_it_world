"""Markdown 文档切分。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


@dataclass
class TextChunk:
    text: str
    chunk_index: int


def split_markdown(content: str) -> List[TextChunk]:
    """
    将 Markdown 正文切分为 Chunk 列表。
    优先按标题与段落边界切分，保留代码块完整性（由 RecursiveCharacterTextSplitter 处理）。
    """
    if not content or not content.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    pieces = splitter.split_text(content.strip())
    chunks: List[TextChunk] = []
    for index, piece in enumerate(pieces):
        text = piece.strip()
        if text:
            chunks.append(TextChunk(text=text, chunk_index=index))
    return chunks
