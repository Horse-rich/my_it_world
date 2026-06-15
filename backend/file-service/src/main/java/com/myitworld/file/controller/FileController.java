package com.myitworld.file.controller;

import com.myitworld.common.constant.AuthConstants;
import com.myitworld.common.result.Result;
import com.myitworld.file.dto.FileUploadResponse;
import com.myitworld.file.service.FileService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;

@Tag(name = "文件服务", description = "图片上传与公开访问")
@RestController
@RequestMapping("/api/files")
@RequiredArgsConstructor
public class FileController {

    private static final String PUBLIC_PREFIX = "/api/files/public/";

    private final FileService fileService;

    @Operation(summary = "上传图片（Admin）")
    @PostMapping("/upload")
    public Result<FileUploadResponse> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "bizType", defaultValue = "general") String bizType,
            HttpServletRequest request) {
        Long uploaderId = parseUserId(request.getHeader(AuthConstants.HEADER_USER_ID));
        return Result.success(fileService.upload(file, bizType, uploaderId));
    }

    @Operation(summary = "公开读取文件")
    @GetMapping("/public/**")
    public ResponseEntity<InputStreamResource> getPublicFile(HttpServletRequest request) throws Exception {
        String uri = request.getRequestURI();
        int idx = uri.indexOf(PUBLIC_PREFIX);
        if (idx < 0) {
            return ResponseEntity.notFound().build();
        }
        String objectKey = URLDecoder.decode(uri.substring(idx + PUBLIC_PREFIX.length()), StandardCharsets.UTF_8);

        FileService.FileStream fileStream = fileService.getPublicFile(objectKey);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(fileStream.contentType()))
                .header(HttpHeaders.CACHE_CONTROL, "public, max-age=86400")
                .body(new InputStreamResource(fileStream.stream()));
    }

    @Operation(summary = "删除文件（Admin）")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        fileService.delete(id);
        return Result.success();
    }

    private Long parseUserId(String header) {
        if (header == null || header.isBlank()) {
            return null;
        }
        try {
            return Long.parseLong(header);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
