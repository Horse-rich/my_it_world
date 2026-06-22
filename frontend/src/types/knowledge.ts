export interface KnowledgeSettings {
  guestRagEnabled: boolean;
  userRagEnabled: boolean;
  updatedAt?: string;
}

export interface KnowledgeAccess {
  guestRagEnabled: boolean;
  userRagEnabled: boolean;
  currentUserAllowed: boolean;
  currentUserType: 'guest' | 'user';
  updatedAt?: string;
}

export interface DocumentIndexStatus {
  blogId: number;
  title?: string;
  status: 'pending' | 'processing' | 'done' | 'failed';
  chunkCount: number;
  errorMsg?: string;
  lastIndexedAt?: string;
  updatedAt?: string;
}

export interface IngestHealth {
  qdrantOk: boolean;
  collection: string;
  pointCount: number;
  error?: string;
}

export interface IngestBlogResult {
  blogId: number;
  title?: string;
  status: string;
  chunkCount: number;
  lastIndexedAt?: string;
}

export interface IngestRebuildResult {
  success: number;
  failed: number;
  skipped: number;
  errors: { blogId: number; message: string }[];
}

export interface IngestSearchHit {
  score: number;
  blogId: number;
  title: string;
  chunkIndex: number;
  sourceUrl: string;
  text: string;
  publishTime?: string;
}

export interface KnowledgeBlogRow {
  id: number;
  title: string;
  status: number;
  publishTime?: string;
  indexStatus?: DocumentIndexStatus['status'];
  chunkCount?: number;
  lastIndexedAt?: string;
  errorMsg?: string;
}
