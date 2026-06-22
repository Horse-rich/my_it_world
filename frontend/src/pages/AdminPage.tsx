import { Card, Typography, Space, Button } from 'antd';
import { SafetyCertificateOutlined, FileTextOutlined, UserOutlined, BulbOutlined, ProjectOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

const { Title, Paragraph, Text } = Typography;

/**
 * 管理后台首页：入口导航
 */
export default function AdminPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Title level={3}>
            <SafetyCertificateOutlined /> 管理后台
          </Title>
          <Paragraph>
            当前用户：<Text strong>{user?.username}</Text>
          </Paragraph>
          <Space wrap>
            <Button type="primary" icon={<FileTextOutlined />} onClick={() => navigate('/admin/blogs')}>
              博客管理
            </Button>
            <Button icon={<UserOutlined />} onClick={() => navigate('/admin/about')}>
              关于我
            </Button>
            <Button icon={<BulbOutlined />} onClick={() => navigate('/admin/skills')}>
              技能管理
            </Button>
            <Button icon={<ProjectOutlined />} onClick={() => navigate('/admin/projects')}>
              项目管理
            </Button>
            <Button icon={<DatabaseOutlined />} onClick={() => navigate('/admin/knowledge')}>
              知识库管理
            </Button>
          </Space>
        </Space>
      </Card>
    </div>
  );
}
