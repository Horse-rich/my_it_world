-- ============================================================
-- file-service 文件元数据表
-- 执行：mysql -u root -p myit_world < deploy/sql/file_migration.sql
-- ============================================================
USE myit_world;

CREATE TABLE IF NOT EXISTS file_record (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    original_name VARCHAR(256) NOT NULL COMMENT '原始文件名',
    object_key    VARCHAR(512) NOT NULL COMMENT 'MinIO 对象键',
    content_type  VARCHAR(128)          DEFAULT NULL COMMENT 'MIME 类型',
    file_size     BIGINT       NOT NULL COMMENT '文件大小（字节）',
    biz_type      VARCHAR(32)  NOT NULL DEFAULT 'general' COMMENT '业务类型：avatar/cover/general',
    uploader_id   BIGINT                DEFAULT NULL COMMENT '上传者用户 ID',
    deleted       TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除',
    create_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_object_key (object_key),
    KEY idx_uploader (uploader_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件上传记录';
