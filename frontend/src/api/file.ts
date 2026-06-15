import request from '@/utils/request';
import { ApiResult } from '@/types/auth';
import { FileUploadResult } from '@/types/file';

/** Admin：上传图片（头像、封面等） */
export async function uploadImage(
  file: File,
  bizType: 'avatar' | 'cover' | 'general' = 'general'
): Promise<FileUploadResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('bizType', bizType);
  const res = await request.post<ApiResult<FileUploadResult>>('/api/files/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return res.data.data;
}
