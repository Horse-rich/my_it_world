import { Layout, Menu, Button, Space, Typography, Dropdown } from 'antd';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  HomeOutlined,
  LoginOutlined,
  LogoutOutlined,
  UserOutlined,
  DashboardOutlined,
  ReadOutlined,
  RobotOutlined,
  InfoCircleOutlined,
  BulbOutlined,
  ProjectOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/stores/authStore';
import { useAuthBootstrap } from '@/hooks/useAuthBootstrap';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

/**
 * 主布局组件
 * <p>
 * 包含顶部导航栏、内容区域、页脚。
 * 根据登录态显示「登录/注册」或「用户菜单」。
 * </p>
 */
export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout, isAdmin, loading } = useAuthStore();

  useAuthBootstrap();

  /** 顶部导航菜单项 */
  const menuItems = [
    { key: '/', icon: <HomeOutlined />, label: <Link to="/">首页</Link> },
    { key: '/about', icon: <InfoCircleOutlined />, label: <Link to="/about">关于</Link> },
    { key: '/skills', icon: <BulbOutlined />, label: <Link to="/skills">技能</Link> },
    { key: '/projects', icon: <ProjectOutlined />, label: <Link to="/projects">项目</Link> },
    { key: '/blogs', icon: <ReadOutlined />, label: <Link to="/blogs">博客</Link> },
    { key: '/assistant', icon: <RobotOutlined />, label: <Link to="/assistant">AI 助手</Link> },
  ];

  const selectedKey = (() => {
    if (location.pathname.startsWith('/blogs')) return '/blogs';
    if (location.pathname.startsWith('/assistant')) return '/assistant';
    if (location.pathname.startsWith('/projects')) return '/projects';
    if (location.pathname.startsWith('/skills')) return '/skills';
    if (location.pathname.startsWith('/about')) return '/about';
    return location.pathname;
  })();

  /** 用户下拉菜单 */
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: user?.username || '用户',
      disabled: true,
    },
    ...(isAdmin()
      ? [
          {
            key: 'admin',
            icon: <DashboardOutlined />,
            label: '管理后台',
            onClick: () => navigate('/admin'),
          },
        ]
      : []),
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: async () => {
        await logout();
        navigate('/login');
      },
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#001529',
          padding: '0 24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <Text style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>
            My IT World
          </Text>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[selectedKey]}
            items={menuItems}
            style={{ flex: 1, minWidth: 200, border: 'none' }}
          />
        </div>

        <Space>
          {isAuthenticated ? (
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Button type="text" icon={<UserOutlined />} style={{ color: '#fff' }}>
                {loading && !user ? '...' : user?.username}
              </Button>
            </Dropdown>
          ) : (
            <Button
              type="primary"
              icon={<LoginOutlined />}
              onClick={() => navigate('/login')}
            >
              登录
            </Button>
          )}
        </Space>
      </Header>

      <Content style={{ padding: '24px 48px', background: '#f5f5f5' }}>
        <Outlet />
      </Content>

      <Footer style={{ textAlign: 'center', color: '#999' }}>
        My IT World © {new Date().getFullYear()} — 个人 IT 学习成果展示平台
      </Footer>
    </Layout>
  );
}
