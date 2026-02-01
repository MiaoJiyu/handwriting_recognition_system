import React from 'react';
import { Card, Form, Input, Button, Alert, Descriptions, Typography, message, Space } from 'antd';
import { LockOutlined, UserOutlined, SafetyOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const { Title } = Typography;

const UserCenter: React.FC = () => {
  const { user } = useAuth();
  const [form] = Form.useForm();

  // 修改密码的mutation
  const changePasswordMutation = useMutation({
    mutationFn: async (data: { old_password: string; new_password: string }) => {
      const res = await api.post('/auth/change-password', data);
      return res.data;
    },
    onSuccess: (data) => {
      message.success(data.message || '密码修改成功');
      form.resetFields();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '密码修改失败');
    },
  });

  const handleSubmit = (values: any) => {
    changePasswordMutation.mutate({
      old_password: values.old_password,
      new_password: values.new_password,
    });
  };

  // 角色名称映射
  const roleMap: Record<string, string> = {
    'system_admin': '系统管理员',
    'school_admin': '学校管理员',
    'teacher': '教师',
    'student': '学生',
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>用户中心</Title>

      {/* 用户信息卡片 */}
      <Card
        title={
          <Space>
            <UserOutlined />
            基本信息
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Descriptions column={2} bordered>
          <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
          <Descriptions.Item label="昵称">
            {user?.nickname || '未设置'}
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            {roleMap[user?.role || ''] || user?.role}
          </Descriptions.Item>
          <Descriptions.Item label="用户ID">{user?.id}</Descriptions.Item>
          {user?.school_id && (
            <Descriptions.Item label="学校ID">{user?.school_id}</Descriptions.Item>
          )}
          {user?.created_at && (
            <Descriptions.Item label="注册时间">
              {new Date(user.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* 修改密码卡片 */}
      <Card
        title={
          <Space>
            <SafetyOutlined />
            安全设置
          </Space>
        }
      >
        <Alert
          message="密码安全提示"
          description="为了您的账户安全，建议定期更换密码。新密码长度不能少于6位。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          style={{ maxWidth: 500 }}
        >
          <Form.Item
            label="原密码"
            name="old_password"
            rules={[
              { required: true, message: '请输入原密码' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请输入原密码"
            />
          </Form.Item>

          <Form.Item
            label="新密码"
            name="new_password"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码长度不能少于6位' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请输入新密码（至少6位）"
            />
          </Form.Item>

          <Form.Item
            label="确认新密码"
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请再次输入新密码"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SafetyOutlined />}
              loading={changePasswordMutation.isPending}
              block
            >
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default UserCenter;
