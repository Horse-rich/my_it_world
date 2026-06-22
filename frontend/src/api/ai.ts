import request from '@/utils/request';
import { ApiResult } from '@/types/auth';
import { getAccessToken } from '@/utils/token';
import {
  ChatRequest,
  ChatResponseData,
  ChatStreamDoneData,
  ChatStreamHandlers,
  ChatSource,
  SessionListData,
  SessionMessagesData,
  SessionSummary,
} from '@/types/ai';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * AI 对话（同步，含 RAG）
 */
export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponseData> {
  const res = await request.post<ApiResult<ChatResponseData>>('/api/ai/chat', payload, {
    timeout: 120000,
  });
  return res.data.data;
}

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split('\n');
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event, data: dataLines.join('\n') };
}

/**
 * AI 流式对话（SSE，含 RAG 引用来源）
 */
export async function sendChatMessageStream(
  payload: ChatRequest,
  handlers: ChatStreamHandlers
): Promise<void> {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE}/api/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const err = await response.json();
      message = err.message || message;
    } catch {
      // ignore
    }
    handlers.onError?.(message);
    throw new Error(message);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('浏览器不支持流式响应');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      const parsed = parseSseBlock(part.trim());
      if (!parsed) {
        continue;
      }
      const payloadData = JSON.parse(parsed.data) as Record<string, unknown>;

      if (parsed.event === 'source') {
        handlers.onSource?.(
          (payloadData.sources as ChatSource[]) ?? [],
          Boolean(payloadData.ragEnabled)
        );
      } else if (parsed.event === 'token') {
        handlers.onToken(String(payloadData.content ?? ''));
      } else if (parsed.event === 'done') {
        handlers.onDone(payloadData as unknown as ChatStreamDoneData);
      } else if (parsed.event === 'error') {
        const message = String(payloadData.message ?? 'AI 调用失败');
        handlers.onError?.(message);
        throw new Error(message);
      }
    }
  }
}

/** 我的会话列表（需登录） */
export async function listChatSessions(page = 1, size = 20): Promise<SessionListData> {
  const res = await request.get<ApiResult<SessionListData>>('/api/ai/sessions', {
    params: { page, size },
  });
  return res.data.data;
}

/** 获取某会话全部消息 */
export async function getSessionMessages(sessionId: string): Promise<SessionMessagesData> {
  const res = await request.get<ApiResult<SessionMessagesData>>(
    `/api/ai/sessions/${sessionId}/messages`
  );
  return res.data.data;
}

/** 修改会话标题 */
export async function updateChatSession(
  sessionId: string,
  title: string
): Promise<SessionSummary> {
  const res = await request.put<ApiResult<SessionSummary>>(`/api/ai/sessions/${sessionId}`, {
    title,
  });
  return res.data.data;
}

/** 删除会话 */
export async function deleteChatSession(sessionId: string): Promise<void> {
  await request.delete(`/api/ai/sessions/${sessionId}`);
}
