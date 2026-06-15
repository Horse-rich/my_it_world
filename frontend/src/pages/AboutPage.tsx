import { useEffect, useState } from 'react';
import { Card, Spin, Typography, Space, Tag, Avatar } from 'antd';
import { UserOutlined, MailOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { fetchAbout } from '@/api/content';
import { AboutInfo } from '@/types/content';
import MarkdownViewer from '@/components/MarkdownViewer';

const { Title, Paragraph, Text } = Typography;

export default function AboutPage() {
  const [loading, setLoading] = useState(true);
  const [about, setAbout] = useState<AboutInfo | null>(null);

  useEffect(() => {
    fetchAbout()
      .then(setAbout)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  if (!about) {
    return <Paragraph type="secondary">暂无关于我内容</Paragraph>;
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <Card>
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <Avatar
            size={120}
            src={about.avatarUrl}
            icon={<UserOutlined />}
            style={{ flexShrink: 0 }}
          />
          <div style={{ flex: 1, minWidth: 240 }}>
            <Title level={2} style={{ marginTop: 0 }}>
              关于我
            </Title>
            {about.slogan && (
              <Paragraph type="secondary" style={{ fontSize: 16 }}>{about.slogan}</Paragraph>
            )}
            {about.summary && <Paragraph>{about.summary}</Paragraph>}
          </div>
        </div>
        <Space wrap style={{ marginBottom: 16 }}>
          {about.email && (
            <Tag icon={<MailOutlined />}>{about.email}</Tag>
          )}
          {about.location && (
            <Tag icon={<EnvironmentOutlined />}>{about.location}</Tag>
          )}
          {about.githubUrl && (
            <a href={about.githubUrl} target="_blank" rel="noreferrer">GitHub</a>
          )}
          {about.csdnUrl && (
            <a href={about.csdnUrl} target="_blank" rel="noreferrer">CSDN</a>
          )}
        </Space>
        {about.content && <MarkdownViewer content={about.content} />}
      </Card>
    </div>
  );
}
