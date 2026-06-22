import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from '@/layouts/MainLayout';
import AuthGuard from '@/components/AuthGuard';
import HomePage from '@/pages/HomePage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import AdminPage from '@/pages/AdminPage';
import BlogListPage from '@/pages/BlogListPage';
import BlogDetailPage from '@/pages/BlogDetailPage';
import BlogAdminPage from '@/pages/admin/BlogAdminPage';
import BlogEditPage from '@/pages/admin/BlogEditPage';
import AssistantPage from '@/pages/AssistantPage';
import AboutPage from '@/pages/AboutPage';
import SkillsPage from '@/pages/SkillsPage';
import ProjectListPage from '@/pages/ProjectListPage';
import ProjectDetailPage from '@/pages/ProjectDetailPage';
import AboutAdminPage from '@/pages/admin/AboutAdminPage';
import SkillsAdminPage from '@/pages/admin/SkillsAdminPage';
import ProjectsAdminPage from '@/pages/admin/ProjectsAdminPage';
import KnowledgeAdminPage from '@/pages/admin/KnowledgeAdminPage';

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/skills" element={<SkillsPage />} />
            <Route path="/projects" element={<ProjectListPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/blogs" element={<BlogListPage />} />
            <Route path="/blogs/:id" element={<BlogDetailPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route element={<AuthGuard requireAuth requireAdmin />}>
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/admin/blogs" element={<BlogAdminPage />} />
              <Route path="/admin/blogs/new" element={<BlogEditPage />} />
              <Route path="/admin/blogs/edit/:id" element={<BlogEditPage />} />
              <Route path="/admin/about" element={<AboutAdminPage />} />
              <Route path="/admin/skills" element={<SkillsAdminPage />} />
              <Route path="/admin/projects" element={<ProjectsAdminPage />} />
              <Route path="/admin/knowledge" element={<KnowledgeAdminPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
