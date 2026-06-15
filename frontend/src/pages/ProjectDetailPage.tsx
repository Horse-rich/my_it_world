import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, Spin, Tag, Typography, Space, Button, message } from 'antd';
import { ArrowLeftOutlined, GithubOutlined, LinkOutlined } from '@ant-design/icons';
import { fetchProjectDetail } from '@/api/content';
import { ProjectItem } from '@/types/content';

const { Title, Paragraph } = Typography;

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<ProjectItem | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchProjectDetail(Number(id))
      .then(setProject)
      .catch((e) => message.error(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  if (!project) return null;

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
        <Link to="/projects">返回项目列表</Link>
      </Button>
      <Card
        cover={
          project.coverUrl ? (
            <img
              alt={project.name}
              src={project.coverUrl}
              style={{ maxHeight: 320, objectFit: 'cover' }}
            />
          ) : undefined
        }
      >
        <Title level={2}>{project.name}</Title>
        {project.featured === 1 && <Tag color="gold">精选项目</Tag>}
        <Paragraph style={{ marginTop: 16 }}>{project.description}</Paragraph>
        <Space wrap style={{ marginBottom: 16 }}>
          {(project.techStack ?? []).map((t) => <Tag key={t} color="blue">{t}</Tag>)}
        </Space>
        <Space>
          {project.githubUrl && (
            <Button icon={<GithubOutlined />} href={project.githubUrl} target="_blank">
              GitHub
            </Button>
          )}
          {project.demoUrl && (
            <Button icon={<LinkOutlined />} href={project.demoUrl} target="_blank">
              在线演示
            </Button>
          )}
        </Space>
      </Card>
    </div>
  );
}
