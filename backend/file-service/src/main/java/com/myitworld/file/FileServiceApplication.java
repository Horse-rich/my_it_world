package com.myitworld.file;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * 文件服务启动类
 * <p>
 * 职责：图片上传至 MinIO、公开读代理、文件元数据记录。
 * </p>
 */
@SpringBootApplication(scanBasePackages = {"com.myitworld.file", "com.myitworld.common"})
@EnableDiscoveryClient
@MapperScan("com.myitworld.file.mapper")
public class FileServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(FileServiceApplication.class, args);
    }
}
