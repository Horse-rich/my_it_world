import { create } from 'zustand';
import {
  deleteChatSession,
  getSessionMessages,
  listChatSessions,
  sendChatMessageStream,
} from '@/api/ai';
import { ChatMessage, SessionSummary } from '@/types/ai';

/** 本地记录最近一次会话 ID（游客与登录用户共用） */
const LAST_SESSION_KEY = 'ai_chat_session_id';

interface ChatState {
  sessions: SessionSummary[];
  sessionsLoading: boolean;
  currentSessionId: string | undefined;
  messages: ChatMessage[];
  messagesLoading: boolean;
  sending: boolean;

  initChat: (isAuthenticated: boolean) => Promise<void>;
  loadSessions: () => Promise<void>;
  loadMessages: (sessionId: string) => Promise<boolean>;
  sendMessage: (text: string) => Promise<void>;
  newChat: () => void;
  selectSession: (sessionId: string) => Promise<void>;
  removeSession: (sessionId: string) => Promise<void>;
  restoreLastSession: () => Promise<void>;
  persistLastSession: (sessionId: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  sessionsLoading: false,
  currentSessionId: undefined,
  messages: [],
  messagesLoading: false,
  sending: false,

  initChat: async (isAuthenticated: boolean) => {
    if (isAuthenticated) {
      await get().loadSessions();
    }
    await get().restoreLastSession();
  },

  loadSessions: async () => {
    set({ sessionsLoading: true });
    try {
      const data = await listChatSessions();
      set({ sessions: data.list, sessionsLoading: false });
    } catch {
      set({ sessionsLoading: false });
    }
  },

  loadMessages: async (sessionId: string) => {
    set({ messagesLoading: true, currentSessionId: sessionId });
    try {
      const data = await getSessionMessages(sessionId);
      set({
        messages: data.messages,
        messagesLoading: false,
        currentSessionId: data.session_id,
      });
      return true;
    } catch {
      set({ messagesLoading: false, messages: [], currentSessionId: undefined });
      return false;
    }
  },

  sendMessage: async (text: string) => {
    const { currentSessionId, messages, sending } = get();
    if (!text.trim() || sending) return;

    const userMsg: ChatMessage = { role: 'user', content: text.trim() };
    const assistantMsg: ChatMessage = { role: 'assistant', content: '' };
    set({
      messages: [...messages, userMsg, assistantMsg],
      sending: true,
    });

    const updateAssistant = (patch: Partial<ChatMessage>) => {
      set((state) => {
        const next = [...state.messages];
        const lastIdx = next.length - 1;
        if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
          next[lastIdx] = { ...next[lastIdx], ...patch };
        }
        return { messages: next };
      });
    };

    try {
      await sendChatMessageStream(
        {
          message: text.trim(),
          session_id: currentSessionId,
        },
        {
          onSource: (sources, ragEnabled) => {
            updateAssistant({ sources, ragEnabled });
          },
          onToken: (chunk) => {
            set((state) => {
              const next = [...state.messages];
              const lastIdx = next.length - 1;
              if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
                next[lastIdx] = {
                  ...next[lastIdx],
                  content: next[lastIdx].content + chunk,
                };
              }
              return { messages: next };
            });
          },
          onDone: (data) => {
            updateAssistant({
              id: data.messageId,
              ragEnabled: data.ragEnabled,
            });
            set({
              currentSessionId: data.sessionId,
              sending: false,
            });
            get().persistLastSession(data.sessionId);
            get().loadSessions();
          },
          onError: (message) => {
            updateAssistant({ content: `抱歉，请求失败：${message}` });
            set({ sending: false });
          },
        }
      );
    } catch (e) {
      set((state) => {
        const next = [...state.messages];
        const lastIdx = next.length - 1;
        if (lastIdx >= 0 && next[lastIdx].role === 'assistant' && !next[lastIdx].content) {
          next[lastIdx] = {
            ...next[lastIdx],
            content: `抱歉，请求失败：${e instanceof Error ? e.message : '未知错误'}`,
          };
        }
        return { messages: next, sending: false };
      });
    }
  },

  newChat: () => {
    set({ currentSessionId: undefined, messages: [] });
    localStorage.removeItem(LAST_SESSION_KEY);
    get().loadSessions();
  },

  selectSession: async (sessionId: string) => {
    await get().loadMessages(sessionId);
    get().persistLastSession(sessionId);
  },

  removeSession: async (sessionId: string) => {
    await deleteChatSession(sessionId);
    const { currentSessionId } = get();
    set((state) => ({
      sessions: state.sessions.filter((s) => s.session_id !== sessionId),
    }));
    if (currentSessionId === sessionId) {
      get().newChat();
    }
  },

  restoreLastSession: async () => {
    const { messages, currentSessionId, sessions } = get();
    if (messages.length > 0 && currentSessionId) {
      return;
    }

    const saved = localStorage.getItem(LAST_SESSION_KEY);
    if (saved) {
      const ok = await get().loadMessages(saved);
      if (ok) {
        return;
      }
      localStorage.removeItem(LAST_SESSION_KEY);
    }

    if (sessions.length > 0) {
      await get().loadMessages(sessions[0].session_id);
      get().persistLastSession(sessions[0].session_id);
    }
  },

  persistLastSession: (sessionId: string) => {
    localStorage.setItem(LAST_SESSION_KEY, sessionId);
  },
}));

export { LAST_SESSION_KEY };
