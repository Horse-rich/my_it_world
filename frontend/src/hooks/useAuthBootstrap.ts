import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { isLoggedIn } from '@/utils/token';

/**
 * 页面刷新后从 Token 恢复用户信息（/api/auth/me）。
 * 应在 MainLayout 等全局布局中调用，避免仅访问 /admin 时才恢复登录态。
 */
export function useAuthBootstrap() {
  const { user, fetchUser } = useAuthStore();

  useEffect(() => {
    if (isLoggedIn() && !user) {
      fetchUser();
    }
  }, [user, fetchUser]);
}
