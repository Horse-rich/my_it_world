import { useEffect, useState } from 'react';
import { Card, Col, Row, Typography, Tag, Space, List, Button, Spin, Avatar } from 'antd';
import { Link } from 'react-router-dom';
import {
  RocketOutlined,
  ReadOutlined,
  ProjectOutlined,
  GithubOutlined,
} from '@ant-design/icons';
import { fetchHome } from '@/api/content';
import { HomeData } from '@/types/content';

const { Title, Paragraph, Text } = Typography;

/**
 * 首页：个人简介 + 精选技能 + 精选项目 + 最新博客
 */
export default function HomePage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<HomeData | null>(null);

  useEffect(() => {
    fetchHome()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  const about = data?.about;

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
          <Avatar size={72} src={about?.avatarUrl} icon={<RocketOutlined />} />
          <div style={{ flex: 1, minWidth: 200 }}>
            <Title level={2} style={{ marginBottom: 8 }}>
              {about?.slogan || '欢迎来到 My IT World'}
            </Title>
            <Paragraph style={{ marginBottom: 8 }}>{about?.summary}</Paragraph>
            <Space wrap>
              {about?.location && <Tag>{about.location}</Tag>}
              {about?.githubUrl && (
                <a href={about.githubUrl} target="_blank" rel="noreferrer">
                  <GithubOutlined /> GitHub
                </a>
              )}
              {about?.csdnUrl && (
                <a href={about.csdnUrl} target="_blank" rel="noreferrer">CSDN</a>
              )}
            </Space>
            <div style={{ marginTop: 12 }}>
              <Button type="link" style={{ paddingLeft: 0 }}>
                <Link to="/about">了解更多 →</Link>
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card
            title="精选技能"
            extra={<Link to="/skills">全部</Link>}
            style={{ height: '100%' }}
          >
            {data?.featuredSkills?.length ? (
              <Space wrap>
                {data.featuredSkills.map((s) => (
                  <Tag key={s.id} color="blue">
                    {s.name} · Lv{s.level}
                  </Tag>
                ))}
              </Space>
            ) : (
              <Text type="secondary">暂无技能数据</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card
            title={<><ProjectOutlined /> 精选项目</>}
            extra={<Link to="/projects">全部</Link>}
            style={{ height: '100%' }}
          >
            <List
              size="small"
              dataSource={data?.featuredProjects ?? []}
              locale={{ emptyText: '暂无项目' }}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      item.coverUrl ? (
                        <img
                          src={item.coverUrl}
                          alt={item.name}
                          style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6 }}
                        />
                      ) : undefined
                    }
                    title={<Link to={`/projects/${item.id}`}>{item.name}</Link>}
                    description={item.description?.slice(0, 60)}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={<><ReadOutlined /> 最新博客</>}
        extra={<Link to="/blogs">查看全部</Link>}
        style={{ marginTop: 16 }}
      >
        <List
          dataSource={data?.latestBlogs ?? []}
          locale={{ emptyText: '暂无文章' }}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={<Link to={`/blogs/${item.id}`}>{item.title}</Link>}
                description={item.summary}
              />
              <Text type="secondary">{item.publishTime?.slice(0, 10)}</Text>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
