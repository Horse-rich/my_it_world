-- ============================================================
-- AI 知识库索引状态表（RAG Ingest 一期）
-- 数据库：myit_world
-- ============================================================

USE myit_world;

CREATE TABLE IF NOT EXISTS ai_document_index (
    id              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    blog_id         BIGINT       NOT NULL COMMENT '关联 blog_article.id',
    title           VARCHAR(256)          DEFAULT NULL COMMENT '文章标题（冗余）',
    status          VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending/processing/done/failed',
    chunk_count     INT          NOT NULL DEFAULT 0 COMMENT '向量 Chunk 数量',
    error_msg       VARCHAR(512)          DEFAULT NULL COMMENT '失败原因',
    last_indexed_at DATETIME              DEFAULT NULL COMMENT '最后成功入库时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_blog_id (blog_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 文档向量索引状态';
