package com.myitworld.file.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("file_record")
public class FileRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String originalName;

    private String objectKey;

    private String contentType;

    private Long fileSize;

    /** avatar / cover / general */
    private String bizType;

    private Long uploaderId;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
}
