"""
My IT World AI Service
FastAPI 入口，端口默认 8090。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.ingest import router as ingest_router
from app.api.knowledge import router as knowledge_router
from app.api.sessions import router as sessions_router
from app.services.vector_store import get_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时确保 Qdrant Collection 存在。"""
    try:
        get_vector_store().ensure_collection()
    except Exception:
        # Qdrant 未就绪时不阻塞对话服务启动
        pass
    yield


app = FastAPI(
    title="My IT World AI Service",
    description="通义千问对话 + RAG 知识库入库",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(ingest_router)
app.include_router(knowledge_router)


@app.get("/")
def root() -> dict:
    return {"service": "ai-service", "docs": "/docs"}
