/** RAG 引用来源 */
export interface ChatSource {
  blogId: number;
  title: string;
  sourceUrl: string;
  chunkIndex: number;
  score: number;
  textPreview?: string;
}

/** AI 聊天消息 */
export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  sources?: ChatSource[];
  ragEnabled?: boolean;
}

/** AI 聊天请求 */
export interface ChatRequest {
  message: string;
  session_id?: string;
}

/** AI 聊天响应数据 */
export interface ChatResponseData {
  content: string;
  session_id: string;
  model: string;
  message_id?: number;
  sources?: ChatSource[];
  ragEnabled?: boolean;
}

/** SSE 流式完成事件 */
export interface ChatStreamDoneData {
  sessionId: string;
  model: string;
  messageId?: number;
  ragEnabled?: boolean;
}

/** 会话列表项 */
export interface SessionSummary {
  session_id: string;
  title?: string;
  model: string;
  updated_at: string;
  created_at: string;
}

/** 会话分页列表 */
export interface SessionListData {
  list: SessionSummary[];
  total: number;
  page: number;
  size: number;
}

/** 会话消息列表 */
export interface SessionMessagesData {
  session_id: string;
  title?: string;
  messages: ChatMessage[];
}

export interface ChatStreamHandlers {
  onSource?: (sources: ChatSource[], ragEnabled: boolean) => void;
  onToken: (chunk: string) => void;
  onDone: (data: ChatStreamDoneData) => void;
  onError?: (message: string) => void;
}
