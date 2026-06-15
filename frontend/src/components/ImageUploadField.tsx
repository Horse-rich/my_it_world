import { useState } from 'react';
import { Upload, message, Input, Space } from 'antd';
import { LoadingOutlined, PlusOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { uploadImage } from '@/api/file';

interface ImageUploadFieldProps {
  value?: string;
  onChange?: (url: string) => void;
  bizType: 'avatar' | 'cover';
  label?: string;
}

/**
 * 图片上传字段：支持本地上传至 file-service，也保留手动粘贴 URL
 */
export default function ImageUploadField({
  value,
  onChange,
  bizType,
  label = '图片',
}: ImageUploadFieldProps) {
  const [uploading, setUploading] = useState(false);

  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    setUploading(true);
    try {
      const result = await uploadImage(file as File, bizType);
      onChange?.(result.url);
      message.success('上传成功');
      onSuccess?.(result);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '上传失败');
      onError?.(e as Error);
    } finally {
      setUploading(false);
    }
  };

  const uploadButton = (
    <div>
      {uploading ? <LoadingOutlined /> : <PlusOutlined />}
      <div style={{ marginTop: 8 }}>上传</div>
    </div>
  );

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Upload
        listType="picture-card"
        showUploadList={false}
        accept="image/jpeg,image/png,image/gif,image/webp"
        customRequest={handleUpload}
        disabled={uploading}
      >
        {value ? (
          <img
            src={value}
            alt={label}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          uploadButton
        )}
      </Upload>
      <Input
        value={value}
        placeholder="或粘贴图片 URL"
        onChange={(e) => onChange?.(e.target.value)}
        allowClear
      />
    </Space>
  );
}
