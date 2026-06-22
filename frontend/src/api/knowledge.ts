import request from '@/utils/request';
import { ApiResult } from '@/types/auth';
import {
  DocumentIndexStatus,
  IngestBlogResult,
  IngestHealth,
  IngestRebuildResult,
  IngestSearchHit,
  KnowledgeAccess,
  KnowledgeSettings,
} from '@/types/knowledge';

export async function fetchIngestHealth(): Promise<IngestHealth> {
  const res = await request.get<ApiResult<{
    qdrantOk?: boolean;
    qdrant_ok?: boolean;
    collection: string;
    pointCount?: number;
    point_count?: number;
    error?: string;
  }>>('/api/ai/ingest/health');
  const d = res.data.data;
  return {
    qdrantOk: Boolean(d.qdrantOk ?? d.qdrant_ok),
    collection: d.collection,
    pointCount: Number(d.pointCount ?? d.point_count ?? 0),
    error: d.error,
  };
}

export async function fetchIngestStatus(blogId?: number): Promise<DocumentIndexStatus[]> {
  const res = await request.get<ApiResult<DocumentIndexStatus[]>>('/api/ai/ingest/status', {
    params: blogId ? { blogId } : undefined,
  });
  return res.data.data ?? [];
}

export async function ingestBlog(blogId: number): Promise<{ data: IngestBlogResult; message: string }> {
  const res = await request.post<ApiResult<IngestBlogResult>>(`/api/ai/ingest/blog/${blogId}`);
  return { data: res.data.data, message: res.data.message || '任务已下发' };
}

export async function deleteBlogIndex(blogId: number): Promise<void> {
  await request.delete(`/api/ai/ingest/blog/${blogId}`);
}

export async function rebuildBlogIndex(options?: {
  onlyPublished?: boolean;
  skipDone?: boolean;
}): Promise<{ data: IngestRebuildResult; message: string }> {
  const res = await request.post<ApiResult<IngestRebuildResult>>('/api/ai/ingest/rebuild', {
    onlyPublished: options?.onlyPublished ?? true,
    skipDone: options?.skipDone ?? false,
  });
  return { data: res.data.data, message: res.data.message || '批量任务已下发' };
}

export async function testKnowledgeSearch(query: string, topK = 5): Promise<IngestSearchHit[]> {
  const res = await request.post<ApiResult<IngestSearchHit[]>>('/api/ai/ingest/search', {
    query,
    topK,
  });
  return res.data.data ?? [];
}

export async function fetchKnowledgeSettings(): Promise<KnowledgeSettings> {
  const res = await request.get<ApiResult<KnowledgeSettings>>('/api/ai/knowledge/settings');
  return res.data.data;
}

export async function updateKnowledgeSettings(data: KnowledgeSettings): Promise<KnowledgeSettings> {
  const res = await request.put<ApiResult<KnowledgeSettings>>('/api/ai/knowledge/settings', data);
  return res.data.data;
}

export async function fetchKnowledgeAccess(): Promise<KnowledgeAccess> {
  const res = await request.get<ApiResult<KnowledgeAccess>>('/api/ai/knowledge/access');
  return res.data.data;
}
