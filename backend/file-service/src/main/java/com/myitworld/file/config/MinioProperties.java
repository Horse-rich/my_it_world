package com.myitworld.file.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "minio")
public class MinioProperties {

    private String endpoint = "http://127.0.0.1:9000";
    private String accessKey = "minioadmin";
    private String secretKey = "minioadmin123";
    private String bucket = "myit-world";
    /** 对外访问 URL 前缀，经 Gateway 转发 */
    private String publicUrlPrefix = "/api/files/public";
}
