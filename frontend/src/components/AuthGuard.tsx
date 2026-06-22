import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '@/stores/authStore';
import { useAuthBootstrap } from '@/hooks/useAuthBootstrap';
import { isLoggedIn } from '@/utils/token';

interface AuthGuardProps {
  /** 是否需要登录才能访问 */
  requireAuth?: boolean;
  /** 是否需要 ADMIN 角色 */
  requireAdmin?: boolean;
}

/**
 * 路由守卫组件
 * <p>
 * - requireAuth：未登录时重定向到 /login，并记录来源路径
 * - requireAdmin：非管理员重定向到首页
 * - 页面刷新时自动调用 fetchUser 恢复登录态
 * </p>
 */
export default function AuthGuard({ requireAuth = false, requireAdmin = false }: AuthGuardProps) {
  const location = useLocation();
  const { isAuthenticated, user, loading, isAdmin } = useAuthStore();

  useAuthBootstrap();

  // 刷新页面时 Token 在 sessionStorage，但 user 尚未从 /me 拉回，需等待而非误判为无权限
  const bootstrapping = isLoggedIn() && !user;

  if (loading || bootstrapping) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // 需要登录但未认证
  if (requireAuth && !isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  // 需要管理员权限
  if (requireAdmin && !isAdmin()) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
