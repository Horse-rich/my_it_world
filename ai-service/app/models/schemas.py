"""Pydantic 请求/响应模型。"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条对话消息。"""

    id: Optional[int] = None
    role: str = Field(description="user 或 assistant")
    content: str
    created_at: Optional[str] = None
    sources: Optional[List["ChatSource"]] = None
    ragEnabled: Optional[bool] = None


class ChatSource(BaseModel):
    """RAG 引用来源。"""

    blogId: int
    title: str
    sourceUrl: str
    chunkIndex: int
    score: float
    textPreview: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求：仅 session_id + 当前消息，历史由服务端加载。"""

    message: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    session_id: Optional[str] = Field(default=None, description="会话 ID，可选")
    use_agent: Optional[bool] = Field(
        default=None,
        description="是否走 Agent 编排；未指定时由 CHAT_MODE 配置决定",
    )


class ChatResponseData(BaseModel):
    """聊天业务数据。"""

    content: str
    session_id: str
    model: str
    message_id: Optional[int] = None
    sources: Optional[List[ChatSource]] = None
    ragEnabled: Optional[bool] = None


class ChatStreamDoneData(BaseModel):
    """SSE done 事件数据。"""

    session_id: str = Field(alias="sessionId")
    model: str
    message_id: Optional[int] = Field(default=None, alias="messageId")
    rag_enabled: Optional[bool] = Field(default=None, alias="ragEnabled")

    model_config = {"populate_by_name": True}


class SessionSummary(BaseModel):
    """会话列表项。"""

    session_id: str
    title: Optional[str] = None
    model: str
    updated_at: str
    created_at: str


class SessionListData(BaseModel):
    """会话分页列表。"""

    list: List[SessionSummary]
    total: int
    page: int
    size: int


class SessionMessagesData(BaseModel):
    """某会话的全部消息。"""

    session_id: str
    title: Optional[str] = None
    messages: List[ChatMessage]


class UpdateSessionRequest(BaseModel):
    """修改会话标题。"""

    title: str = Field(..., min_length=1, max_length=200)


class IngestBlogResult(BaseModel):
    """单篇博客入库结果。"""

    blogId: int
    title: Optional[str] = None
    status: str
    chunkCount: int
    lastIndexedAt: Optional[str] = None


class DocumentIndexStatus(BaseModel):
    """索引状态项。"""

    blogId: int
    title: Optional[str] = None
    status: str
    chunkCount: int
    errorMsg: Optional[str] = None
    lastIndexedAt: Optional[str] = None
    updatedAt: Optional[str] = None


class IngestSearchRequest(BaseModel):
    """检索验收请求。"""

    query: str = Field(..., min_length=1, max_length=2000)
    topK: int = Field(default=5, ge=1, le=20)


class IngestSearchHit(BaseModel):
    """检索命中项。"""

    score: float
    blogId: int
    title: str
    chunkIndex: int
    sourceUrl: str
    text: str
    publishTime: Optional[str] = None


class KnowledgeSettingsData(BaseModel):
    """知识库访问权限配置。"""

    guestRagEnabled: bool
    userRagEnabled: bool
    updatedAt: Optional[str] = None


class KnowledgeSettingsUpdateRequest(BaseModel):
    guestRagEnabled: bool
    userRagEnabled: bool


class KnowledgeAccessData(BaseModel):
    guestRagEnabled: bool
    userRagEnabled: bool
    currentUserAllowed: bool
    currentUserType: str
    updatedAt: Optional[str] = None


class IngestRebuildRequest(BaseModel):
    onlyPublished: bool = True
    skipDone: bool = False


class IngestRebuildResult(BaseModel):
    success: int
    failed: int
    skipped: int
    errors: List[dict]


class Result(BaseModel):
    """与 Java 微服务统一的响应格式。"""

    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
    timestamp: int = 0
