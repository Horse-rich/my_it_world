import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Spin,
  Avatar,
  Layout,
  List,
  Popconfirm,
  Tag,
} from 'antd';
import {
  RobotOutlined,
  UserOutlined,
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  BookOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/stores/authStore';
import { useChatStore } from '@/stores/chatStore';
import { fetchKnowledgeAccess } from '@/api/knowledge';
import { ChatMessage, ChatSource } from '@/types/ai';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Sider, Content } = Layout;

/** 同一篇文章可能命中多个 chunk，展示时按 blogId 去重，保留最高相似度 */
function dedupeSources(sources: ChatSource[]): ChatSource[] {
  const map = new Map<number, ChatSource>();
  for (const source of sources) {
    const existing = map.get(source.blogId);
    if (!existing || source.score > existing.score) {
      map.set(source.blogId, source);
    }
  }
  return [...map.values()].sort((a, b) => b.score - a.score);
}

function MessageSources({ msg }: { msg: ChatMessage }) {
  if (msg.role !== 'assistant' || !msg.sources?.length) {
    return null;
  }

  const displaySources = dedupeSources(msg.sources);

  return (
    <div style={{ marginTop: 10 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>
        <BookOutlined /> 参考来源
      </Text>
      <List
        size="small"
        style={{ marginTop: 6 }}
        dataSource={displaySources}
        renderItem={(source) => (
          <List.Item style={{ padding: '4px 0', border: 'none' }}>
            <Link to={source.sourceUrl || `/blogs/${source.blogId}`} target="_blank">
              {source.title || `博客 #${source.blogId}`}
            </Link>
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
              相似度 {source.score.toFixed(2)}
            </Text>
          </List.Item>
        )}
      />
    </div>
  );
}

/**
 * AI 助手页面：服务端会话 + RAG 流式回答
 */
export default function AssistantPage() {
  const { isAuthenticated } = useAuthStore();
  const {
    sessions,
    sessionsLoading,
    currentSessionId,
    messages,
    messagesLoading,
    sending,
    sendMessage,
    newChat,
    selectSession,
    removeSession,
    initChat,
  } = useChatStore();

  const [input, setInput] = useState('');
  const [ragAllowed, setRagAllowed] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    initChat(isAuthenticated);
  }, [isAuthenticated, initChat]);

  useEffect(() => {
    fetchKnowledgeAccess()
      .then((access) => setRagAllowed(access.currentUserAllowed))
      .catch(() => setRagAllowed(null));
  }, [isAuthenticated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending, messagesLoading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    await sendMessage(text);
  };

  return (
    <div style={{ width: '100%', maxWidth: 1480, margin: '0 auto' }}>
      <Title level={2} style={{ marginBottom: 8 }}>
        <RobotOutlined /> AI 助手
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 20 }}>
        基于通义千问，支持博客知识库 RAG 检索增强回答（流式输出）；对话历史保存在服务端。
        {ragAllowed === true && (
          <Tag color="green" style={{ marginLeft: 8 }}>
            知识库已启用
          </Tag>
        )}
        {ragAllowed === false && (
          <Tag style={{ marginLeft: 8 }}>知识库未启用</Tag>
        )}
      </Paragraph>

      <Layout style={{ background: 'transparent', gap: 20, minHeight: 'calc(100vh - 220px)' }}>
        {isAuthenticated && (
          <Sider
            width={300}
            theme="light"
            style={{
              background: '#fff',
              borderRadius: 8,
              border: '1px solid #f0f0f0',
              padding: 12,
              minHeight: 'calc(100vh - 240px)',
            }}
          >
            <Button
              type="primary"
              icon={<PlusOutlined />}
              block
              onClick={newChat}
              style={{ marginBottom: 12 }}
            >
              新对话
            </Button>
            {sessionsLoading ? (
              <Spin style={{ display: 'block', textAlign: 'center', padding: 24 }} />
            ) : (
              <List
                size="small"
                dataSource={sessions}
                locale={{ emptyText: '暂无会话' }}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      padding: '8px 4px',
                      background:
                        item.session_id === currentSessionId ? '#e6f4ff' : 'transparent',
                      borderRadius: 6,
                    }}
                    onClick={() => selectSession(item.session_id)}
                    actions={[
                      <Popconfirm
                        title="删除此会话？"
                        onConfirm={() => removeSession(item.session_id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <Button
                          type="text"
                          size="small"
                          icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Popconfirm>,
                    ]}
                  >
                    <Text ellipsis style={{ maxWidth: 210 }}>
                      {item.title || '新对话'}
                    </Text>
                  </List.Item>
                )}
              />
            )}
          </Sider>
        )}

        <Content style={{ display: 'flex', flexDirection: 'column', minHeight: 'calc(100vh - 240px)' }}>
          {!isAuthenticated && (
            <Button icon={<PlusOutlined />} onClick={newChat} style={{ marginBottom: 12 }}>
              新对话
            </Button>
          )}

          <Card
            style={{ flex: 1, marginBottom: 16, display: 'flex', flexDirection: 'column' }}
            styles={{
              body: {
                flex: 1,
                minHeight: 'calc(100vh - 340px)',
                maxHeight: 'calc(100vh - 340px)',
                overflowY: 'auto',
                padding: '20px 24px',
              },
            }}
          >
            {messagesLoading ? (
              <div style={{ textAlign: 'center', padding: 80 }}>
                <Spin tip="加载历史..." />
              </div>
            ) : (
              <>
                {messages.length === 0 && !sending && (
                  <Paragraph type="secondary" style={{ textAlign: 'center', marginTop: 80 }}>
                    输入问题开始对话，例如：「Spring Cloud Gateway 是做什么的？」
                  </Paragraph>
                )}

                {messages.map((msg, idx) => (
                  <div
                    key={msg.id ?? idx}
                    style={{
                      display: 'flex',
                      gap: 12,
                      marginBottom: 16,
                      flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                    }}
                  >
                    <Avatar
                      icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                      style={{
                        background: msg.role === 'user' ? '#1677ff' : '#52c41a',
                        flexShrink: 0,
                      }}
                    />
                    <div
                      style={{
                        maxWidth: msg.role === 'assistant' ? '88%' : '80%',
                        padding: '12px 16px',
                        borderRadius: 8,
                        background: msg.role === 'user' ? '#e6f4ff' : '#f6ffed',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        fontSize: 15,
                        lineHeight: 1.7,
                      }}
                    >
                      {msg.content || (sending && msg.role === 'assistant' ? (
                        <Spin size="small" />
                      ) : null)}
                      <MessageSources msg={msg} />
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </>
            )}
          </Card>

          <Space.Compact style={{ width: '100%' }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入你的问题..."
              autoSize={{ minRows: 3, maxRows: 6 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={sending || messagesLoading}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={sending}
              disabled={messagesLoading}
              style={{ height: 'auto', minHeight: 64 }}
            >
              发送
            </Button>
          </Space.Compact>

          {currentSessionId && (
            <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
              会话 ID：{currentSessionId}
            </Text>
          )}
        </Content>
      </Layout>
    </div>
  );
}
