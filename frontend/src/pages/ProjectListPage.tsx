import { useEffect, useState } from 'react';
import { Card, Col, Row, Spin, Tag, Typography, Button, Space } from 'antd';
import { Link } from 'react-router-dom';
import { GithubOutlined, LinkOutlined, ProjectOutlined } from '@ant-design/icons';
import { fetchProjects } from '@/api/content';
import { ProjectItem } from '@/types/content';

const { Title, Paragraph } = Typography;

export default function ProjectListPage() {
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<ProjectItem[]>([]);

  useEffect(() => {
    fetchProjects()
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <Title level={2}>
        <ProjectOutlined /> 项目作品
      </Title>
      <Paragraph type="secondary">个人学习与实战项目展示</Paragraph>

      <Row gutter={[16, 16]}>
        {projects.map((p) => (
          <Col xs={24} sm={12} key={p.id}>
            <Card
              cover={
                p.coverUrl ? (
                  <img
                    alt={p.name}
                    src={p.coverUrl}
                    style={{ height: 160, objectFit: 'cover' }}
                  />
                ) : undefined
              }
              title={
                <Link to={`/projects/${p.id}`}>{p.name}</Link>
              }
              extra={p.featured === 1 ? <Tag color="gold">精选</Tag> : null}
            >
              <Paragraph ellipsis={{ rows: 3 }}>{p.description}</Paragraph>
              <Space wrap>
                {(p.techStack ?? []).map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </Space>
              <Space style={{ marginTop: 12 }}>
                {p.githubUrl && (
                  <Button size="small" icon={<GithubOutlined />} href={p.githubUrl} target="_blank">
                    源码
                  </Button>
                )}
                {p.demoUrl && (
                  <Button size="small" icon={<LinkOutlined />} href={p.demoUrl} target="_blank">
                    演示
                  </Button>
                )}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
