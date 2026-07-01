"""AI 服务配置：从环境变量读取通义千问 API Key、MySQL、Redis 等。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持 .env 文件与环境变量。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 通义千问 / DashScope API Key
    dashscope_api_key: str = ""

    # 模型：qwen-turbo / qwen-plus / qwen-max 等
    tongyi_model: str = "qwen-turbo"

    # 服务端口
    ai_service_port: int = 8090

    # 系统提示词（简单对话阶段）
    system_prompt: str = (
        "你是 My IT World 个人网站上的 AI 助手，擅长解答编程、云计算、Java、"
        "Spring、前端等技术问题。回答请简洁清晰，使用中文。"
    )

    # MySQL（与 Java 微服务共用 myit_world 库）
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "demo1"
    mysql_database: str = "myit_world"

    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str = ""
    redis_database: int = 0

    # 对话历史：给 LLM 的滑动窗口（消息条数，user+assistant 合计）
    history_window: int = 20

    # Redis 缓存 TTL（秒）：游客会话 7 天
    guest_session_ttl_seconds: int = 7 * 24 * 3600

    # 登录用户会话 Redis TTL（秒），0 表示不过期
    user_session_ttl_seconds: int = 0

    # Gateway 地址（拉取博客正文）
    gateway_base_url: str = "http://127.0.0.1:8080"

    # blog-service 内网地址（入库任务直连，避免后台二次过 Gateway 时 Token 失效）
    blog_service_base_url: str = "http://127.0.0.1:8084"

    # Qdrant 向量库
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "blog_chunks"

    # Embedding：ollama（本地/远程）或 dashscope（百炼）
    embedding_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: float = 120.0
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dimension: int = 1024

    # 文档切分
    chunk_size: int = 800
    chunk_overlap: int = 128

    # 检索默认 Top-K（验收 / RAG 复用）
    search_top_k: int = 5

    # RAG 相似度下限（Cosine，0 表示不过滤）
    rag_min_score: float = 0.0

    # 对话模式：agent（ReAct + 工具）或 rag（固定检索流水线）
    chat_mode: str = "agent"

    # Agent 运行时
    agent_model: str = "qwen-plus"
    agent_max_steps: int = 6
    agent_verbose_log: bool = False

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )


settings = Settings()
