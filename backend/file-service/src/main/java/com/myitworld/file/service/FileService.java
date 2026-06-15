package com.myitworld.file.service;

import com.myitworld.common.exception.BusinessException;
import com.myitworld.common.result.ResultCode;
import com.myitworld.file.config.MinioProperties;
import com.myitworld.file.dto.FileUploadResponse;
import com.myitworld.file.entity.FileRecord;
import com.myitworld.file.mapper.FileRecordMapper;
import io.minio.GetObjectArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.time.LocalDate;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileService {

    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "image/jpeg", "image/png", "image/gif", "image/webp"
    );
    private static final Set<String> ALLOWED_BIZ_TYPES = Set.of("avatar", "cover", "general");
    private static final long MAX_FILE_SIZE = 5 * 1024 * 1024L;

    private final MinioClient minioClient;
    private final MinioProperties minioProperties;
    private final FileRecordMapper fileRecordMapper;

    public FileUploadResponse upload(MultipartFile file, String bizType, Long uploaderId) {
        validateFile(file, bizType);

        String normalizedBiz = normalizeBizType(bizType);
        String ext = extractExtension(file.getOriginalFilename(), file.getContentType());
        LocalDate today = LocalDate.now();
        String objectKey = String.format("images/%s/%d/%02d/%s%s",
                normalizedBiz, today.getYear(), today.getMonthValue(), UUID.randomUUID(), ext);

        try (InputStream inputStream = file.getInputStream()) {
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(minioProperties.getBucket())
                    .object(objectKey)
                    .stream(inputStream, file.getSize(), -1)
                    .contentType(file.getContentType())
                    .build());
        } catch (Exception e) {
            log.error("MinIO upload failed: {}", e.getMessage(), e);
            throw new BusinessException(ResultCode.INTERNAL_ERROR, "文件上传失败");
        }

        FileRecord record = new FileRecord();
        record.setOriginalName(file.getOriginalFilename());
        record.setObjectKey(objectKey);
        record.setContentType(file.getContentType());
        record.setFileSize(file.getSize());
        record.setBizType(normalizedBiz);
        record.setUploaderId(uploaderId);
        fileRecordMapper.insert(record);

        String url = minioProperties.getPublicUrlPrefix() + "/" + objectKey;
        return FileUploadResponse.builder()
                .id(record.getId())
                .url(url)
                .originalName(record.getOriginalName())
                .contentType(record.getContentType())
                .fileSize(record.getFileSize())
                .bizType(normalizedBiz)
                .build();
    }

    public FileStream getPublicFile(String objectKey) {
        if (!StringUtils.hasText(objectKey) || objectKey.contains("..")) {
            throw new BusinessException(ResultCode.NOT_FOUND, "文件不存在");
        }
        try {
            var response = minioClient.getObject(GetObjectArgs.builder()
                    .bucket(minioProperties.getBucket())
                    .object(objectKey)
                    .build());
            String contentType = response.headers().get("Content-Type");
            if (contentType == null) {
                contentType = "application/octet-stream";
            }
            return new FileStream(response, contentType);
        } catch (Exception e) {
            log.warn("MinIO get object failed: key={}, error={}", objectKey, e.getMessage());
            throw new BusinessException(ResultCode.NOT_FOUND, "文件不存在");
        }
    }

    public void delete(Long id) {
        FileRecord record = fileRecordMapper.selectById(id);
        if (record == null) {
            throw new BusinessException(ResultCode.NOT_FOUND, "文件记录不存在");
        }
        try {
            minioClient.removeObject(RemoveObjectArgs.builder()
                    .bucket(minioProperties.getBucket())
                    .object(record.getObjectKey())
                    .build());
        } catch (Exception e) {
            log.warn("MinIO delete failed: id={}, error={}", id, e.getMessage());
        }
        fileRecordMapper.deleteById(id);
    }

    private void validateFile(MultipartFile file, String bizType) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "请选择要上传的文件");
        }
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "文件大小不能超过 5MB");
        }
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "仅支持 JPG、PNG、GIF、WebP 图片");
        }
        normalizeBizType(bizType);
    }

    private String normalizeBizType(String bizType) {
        String type = StringUtils.hasText(bizType) ? bizType.trim().toLowerCase(Locale.ROOT) : "general";
        if (!ALLOWED_BIZ_TYPES.contains(type)) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "bizType 仅支持 avatar、cover、general");
        }
        return type;
    }

    private String extractExtension(String filename, String contentType) {
        if (StringUtils.hasText(filename) && filename.contains(".")) {
            String ext = filename.substring(filename.lastIndexOf('.')).toLowerCase(Locale.ROOT);
            if (ext.matches("\\.(jpe?g|png|gif|webp)")) {
                return ext;
            }
        }
        return switch (contentType) {
            case "image/png" -> ".png";
            case "image/gif" -> ".gif";
            case "image/webp" -> ".webp";
            default -> ".jpg";
        };
    }

    public record FileStream(InputStream stream, String contentType) implements AutoCloseable {
        @Override
        public void close() throws Exception {
            stream.close();
        }
    }
}
