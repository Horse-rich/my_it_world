import { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Col, Descriptions, Form, Input, message, Popconfirm, Row, Space,
  Switch, Table, Tag, Typography, Alert, Modal, List,
} from 'antd';
import {
  CloudSyncOutlined, DatabaseOutlined, DeleteOutlined, SearchOutlined,
  SafetyOutlined, ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { fetchAdminBlogPage } from '@/api/blog';
import {
  deleteBlogIndex,
  fetchIngestHealth,
  fetchIngestStatus,
  fetchKnowledgeSettings,
  ingestBlog,
  rebuildBlogIndex,
  testKnowledgeSearch,
  updateKnowledgeSettings,
} from '@/api/knowledge';
import { KnowledgeBlogRow, KnowledgeSettings } from '@/types/knowledge';
import { STATUS_LABEL } from '@/types/blog';

const { Title, Paragraph, Text } = Typography;

const INDEX_STATUS_MAP: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '未入库' },
  processing: { color: 'processing', label: '入库中' },
  done: { color: 'success', label: '已入库' },
  failed: { color: 'error', label: '失败' },
};

export default function KnowledgeAdminPage() {
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<{ qdrantOk: boolean; pointCount: number; collection: string } | null>(null);
  const [settings, setSettings] = useState<KnowledgeSettings | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [rows, setRows] = useState<KnowledgeBlogRow[]>([]);
  const [rebuilding, setRebuilding] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchHits, setSearchHits] = useState<Awaited<ReturnType<typeof testKnowledgeSearch>>>([]);
  const [searching, setSearching] = useState(false);
  const [syncingId, setSyncingId] = useState<number | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [healthData, settingsData, blogPage, indexList] = await Promise.all([
        fetchIngestHealth(),
        fetchKnowledgeSettings(),
        fetchAdminBlogPage({ page: 1, size: 200 }),
        fetchIngestStatus(),
      ]);

      setHealth({
        qdrantOk: healthData.qdrantOk,
        pointCount: healthData.pointCount,
        collection: healthData.collection,
      });
      setSettings(settingsData);

      const indexMap = new Map(indexList.map((item) => [item.blogId, item]));
      const merged: KnowledgeBlogRow[] = blogPage.records.map((blog) => {
        const idx = indexMap.get(blog.id);
        return {
          id: blog.id,
          title: blog.title,
          status: blog.status,
          publishTime: blog.publishTime,
          indexStatus: idx?.status,
          chunkCount: idx?.chunkCount,
          lastIndexedAt: idx?.lastIndexedAt,
          errorMsg: idx?.errorMsg,
        };
      });
      setRows(merged);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSaveSettings = async (values: KnowledgeSettings) => {
    setSavingSettings(true);
    try {
      const updated = await updateKnowledgeSettings(values);
      setSettings(updated);
      message.success('权限配置已保存');
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleSync = async (blogId: number) => {
    setSyncingId(blogId);
    try {
      const { data, message: tip } = await ingestBlog(blogId);
      message.success(tip);
      setRows((prev) =>
        prev.map((row) =>
          row.id === blogId
            ? { ...row, indexStatus: data.status as KnowledgeBlogRow['indexStatus'], errorMsg: undefined }
            : row
        )
      );
    } catch (e) {
      message.error(e instanceof Error ? e.message : '提交失败');
    } finally {
      setSyncingId(null);
    }
  };

  const handleDeleteIndex = async (blogId: number) => {
    try {
      await deleteBlogIndex(blogId);
      message.success('已删除向量索引');
      await loadAll();
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败');
    }
  };

  const handleRebuild = async (skipDone: boolean) => {
    setRebuilding(true);
    try {
      const { message: tip } = await rebuildBlogIndex({ onlyPublished: true, skipDone });
      message.success(tip);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '提交失败');
    } finally {
      setRebuilding(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      setSearchHits(await testKnowledgeSearch(searchQuery.trim(), 5));
    } catch (e) {
      message.error(e instanceof Error ? e.message : '检索失败');
    } finally {
      setSearching(false);
    }
  };

  const columns: ColumnsType<KnowledgeBlogRow> = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '发布状态',
      dataIndex: 'status',
      width: 90,
      render: (s: number) => <Tag>{STATUS_LABEL[s] ?? s}</Tag>,
    },
    {
      title: '索引状态',
      dataIndex: 'indexStatus',
      width: 100,
      render: (v?: string) => {
        if (!v) return <Tag>未入库</Tag>;
        const meta = INDEX_STATUS_MAP[v] ?? { color: 'default', label: v };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    { title: 'Chunk', dataIndex: 'chunkCount', width: 70, render: (v) => v ?? '-' },
    {
      title: '最后入库',
      dataIndex: 'lastIndexedAt',
      width: 160,
      render: (v) => v?.slice(0, 16) ?? '-',
    },
    {
      title: '操作',
      width: 200,
      render: (_, row) => (
        <Space size="small">
          <Button
            size="small"
            type="primary"
            icon={<CloudSyncOutlined />}
            loading={syncingId === row.id}
            onClick={() => handleSync(row.id)}
          >
            同步
          </Button>
          <Popconfirm title="删除该博客的向量索引？" onConfirm={() => handleDeleteIndex(row.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删索引</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Title level={3}>
        <DatabaseOutlined /> 知识库管理
      </Title>
      <Paragraph type="secondary">
        将博客正文向量化存入 Qdrant；配置游客与登录用户对知识库（RAG 检索）的使用权限。
        同步/批量同步为<strong>异步任务</strong>，提交后请点击「刷新」查看索引状态，无需等待完成。
      </Paragraph>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          <Card title="向量库概况" loading={loading}>
            {health && (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Qdrant">
                  <Tag color={health.qdrantOk ? 'success' : 'error'}>
                    {health.qdrantOk ? '已连接' : '不可用'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Collection">{health.collection}</Descriptions.Item>
                <Descriptions.Item label="向量条数">{health.pointCount}</Descriptions.Item>
              </Descriptions>
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="访问权限" loading={loading}>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message="控制 AI 助手是否使用博客知识库回答（RAG）"
              description="关闭后，对应用户类型仅能使用通用对话，不会检索 Qdrant 中的博客片段。"
            />
            {settings && (
              <Form
                layout="vertical"
                initialValues={settings}
                onFinish={handleSaveSettings}
                key={`${settings.guestRagEnabled}-${settings.userRagEnabled}`}
              >
                <Form.Item
                  name="guestRagEnabled"
                  label="游客（未登录）可使用知识库"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                </Form.Item>
                <Form.Item
                  name="userRagEnabled"
                  label="登录用户可使用知识库"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                </Form.Item>
                {settings.updatedAt && (
                  <Text type="secondary">上次更新：{settings.updatedAt}</Text>
                )}
                <Form.Item style={{ marginTop: 16, marginBottom: 0 }}>
                  <Button type="primary" htmlType="submit" loading={savingSettings} icon={<SafetyOutlined />}>
                    保存权限
                  </Button>
                </Form.Item>
              </Form>
            )}
          </Card>
        </Col>
      </Row>

      <Card
        title="博客索引"
        loading={loading}
        extra={
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={loadAll}>刷新</Button>
            <Button icon={<SearchOutlined />} onClick={() => setSearchOpen(true)}>检索验收</Button>
            <Popconfirm title="批量入库全部已发布博客？" onConfirm={() => handleRebuild(false)}>
              <Button type="primary" icon={<CloudSyncOutlined />} loading={rebuilding}>
                全量同步
              </Button>
            </Popconfirm>
            <Popconfirm title="仅同步尚未成功的博客？" onConfirm={() => handleRebuild(true)}>
              <Button loading={rebuilding}>增量同步</Button>
            </Popconfirm>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={rows}
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender: (row) =>
              row.errorMsg ? (
                <Text type="danger">{row.errorMsg}</Text>
              ) : (
                <Text type="secondary">暂无错误信息</Text>
              ),
            rowExpandable: (row) => Boolean(row.errorMsg),
          }}
        />
      </Card>

      <Modal
        title="检索验收"
        open={searchOpen}
        onCancel={() => setSearchOpen(false)}
        footer={null}
        width={720}
      >
        <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
          <Input
            placeholder="输入问题，测试 Qdrant 检索效果"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onPressEnter={handleSearch}
          />
          <Button type="primary" loading={searching} onClick={handleSearch}>检索</Button>
        </Space.Compact>
        <List
          dataSource={searchHits}
          locale={{ emptyText: '暂无结果，请先同步博客到知识库' }}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color="blue">score {item.score.toFixed(3)}</Tag>
                    <a href={item.sourceUrl} target="_blank" rel="noreferrer">{item.title}</a>
                  </Space>
                }
                description={item.text.slice(0, 200)}
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
}
