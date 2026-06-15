import { useEffect, useState } from 'react';
import {
  Card, Table, Button, Space, Modal, Form, Input, InputNumber, Switch, message, Popconfirm, Select,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  createProject, deleteProject, fetchAdminProjects, updateProject,
} from '@/api/content';
import { ProjectItem, ProjectSaveRequest } from '@/types/content';
import ImageUploadField from '@/components/ImageUploadField';

export default function ProjectsAdminPage() {
  const [list, setList] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ProjectItem | null>(null);
  const [form] = Form.useForm<ProjectSaveRequest & { techStackText?: string }>();

  const load = async () => {
    setLoading(true);
    try {
      setList(await fetchAdminProjects());
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const columns: ColumnsType<ProjectItem> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '精选', dataIndex: 'featured', width: 60, render: (v) => v === 1 ? '是' : '否' },
    { title: '状态', dataIndex: 'status', width: 70, render: (v) => v === 1 ? '展示' : '下架' },
    { title: '排序', dataIndex: 'sortOrder', width: 60 },
    {
      title: '操作',
      width: 180,
      render: (_, row) => (
        <Space>
          <Button size="small" onClick={() => {
            setEditing(row);
            form.setFieldsValue({
              ...row,
              techStackText: (row.techStack ?? []).join(','),
              featured: row.featured === 1,
              status: row.status === 1,
            });
            setModalOpen(true);
          }}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={async () => {
            await deleteProject(row.id!);
            message.success('已删除');
            load();
          }}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const onSave = async () => {
    const values = await form.validateFields();
    const techStack = values.techStackText
      ? values.techStackText.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
      : [];
    const payload: ProjectSaveRequest = {
      name: values.name,
      description: values.description,
      coverUrl: values.coverUrl,
      githubUrl: values.githubUrl,
      demoUrl: values.demoUrl,
      sortOrder: values.sortOrder,
      featured: values.featured ? 1 : 0,
      status: values.status ? 1 : 0,
      techStack,
    };
    if (editing?.id) {
      await updateProject(editing.id, payload);
    } else {
      await createProject(payload);
    }
    message.success('保存成功');
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
    load();
  };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <Card
        title="项目管理"
        extra={
          <Button type="primary" onClick={() => {
            setEditing(null);
            form.resetFields();
            setModalOpen(true);
          }}>新建项目</Button>
        }
      >
        <Table rowKey="id" loading={loading} columns={columns} dataSource={list} />
      </Card>

      <Modal
        title={editing ? '编辑项目' : '新建项目'}
        open={modalOpen}
        onOk={onSave}
        onCancel={() => setModalOpen(false)}
        width={640}
      >
        <Form form={form} layout="vertical" initialValues={{ status: 1, featured: 0, sortOrder: 0 }}>
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="techStackText" label="技术栈（逗号分隔）">
            <Input placeholder="Spring Boot, React, MySQL" />
          </Form.Item>
          <Form.Item name="githubUrl" label="GitHub">
            <Input />
          </Form.Item>
          <Form.Item name="demoUrl" label="演示地址">
            <Input />
          </Form.Item>
          <Form.Item name="coverUrl" label="封面图">
            <ImageUploadField bizType="cover" label="封面" />
          </Form.Item>
          <Form.Item name="sortOrder" label="排序">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item name="featured" label="首页精选" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="status" label="展示" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
