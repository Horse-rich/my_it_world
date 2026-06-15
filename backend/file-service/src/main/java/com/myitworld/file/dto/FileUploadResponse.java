package com.myitworld.file.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class FileUploadResponse {

    private Long id;

    /** 可公开访问的 URL（经 Gateway） */
    private String url;

    private String originalName;

    private String contentType;

    private Long fileSize;

    private String bizType;
}
