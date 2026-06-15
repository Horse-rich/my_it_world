import { useEffect, useState } from 'react';
import { Card, Form, Input, Button, message, Typography } from 'antd';
import { fetchAdminAbout, updateAbout } from '@/api/content';
import { AboutSaveRequest } from '@/types/content';
import ImageUploadField from '@/components/ImageUploadField';

const { Title } = Typography;
const { TextArea } = Input;

export default function AboutAdminPage() {
  const [form] = Form.useForm<AboutSaveRequest>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchAdminAbout()
      .then((data) => form.setFieldsValue(data))
      .catch((e) => message.error(e.message))
      .finally(() => setLoading(false));
  }, [form]);

  const onSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await updateAbout(values);
      message.success('保存成功');
    } catch (e) {
      if (e instanceof Error) message.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card loading={loading}>
        <Title level={4}>编辑关于我</Title>
        <Form form={form} layout="vertical">
          <Form.Item name="slogan" label="Slogan">
            <Input maxLength={256} />
          </Form.Item>
          <Form.Item name="summary" label="简短简介">
            <TextArea rows={2} maxLength={512} />
          </Form.Item>
          <Form.Item name="content" label="详细介绍（Markdown）">
            <TextArea rows={12} />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="location" label="所在地">
            <Input />
          </Form.Item>
          <Form.Item name="githubUrl" label="GitHub">
            <Input />
          </Form.Item>
          <Form.Item name="csdnUrl" label="CSDN">
            <Input />
          </Form.Item>
          <Form.Item name="linkedinUrl" label="LinkedIn">
            <Input />
          </Form.Item>
          <Form.Item name="avatarUrl" label="头像">
            <ImageUploadField bizType="avatar" label="头像" />
          </Form.Item>
          <Button type="primary" onClick={onSave} loading={saving}>
            保存
          </Button>
        </Form>
      </Card>
    </div>
  );
}
