-- ============================================================
-- AI 知识库访问权限配置（单行配置表）
-- ============================================================
USE myit_world;

CREATE TABLE IF NOT EXISTS ai_knowledge_settings (
    id                 INT          NOT NULL DEFAULT 1 COMMENT '固定为 1',
    guest_rag_enabled  TINYINT      NOT NULL DEFAULT 0 COMMENT '游客是否可用知识库检索',
    user_rag_enabled   TINYINT      NOT NULL DEFAULT 1 COMMENT '登录用户是否可用知识库检索',
    updated_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 知识库访问权限';

INSERT INTO ai_knowledge_settings (id, guest_rag_enabled, user_rag_enabled)
VALUES (1, 0, 1)
ON DUPLICATE KEY UPDATE id = id;
