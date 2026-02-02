import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Checkbox,
  Space,
  Tag,
  Popconfirm,
  Alert,
  Descriptions,
  message,
  Tooltip,
  Divider,
  Typography,
  Tabs,
  DatePicker,
  Radio
} from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import utc from 'dayjs/plugin/utc.js';

// Load UTC plugin
dayjs.extend(utc);
import {
  PlusOutlined,
  DeleteOutlined,
  StopOutlined,
  KeyOutlined,
  CopyOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { formatDateToLocal } from '../utils/datetime';
import TokenAPITest from './TokenAPITest';

const { Text, Title, Paragraph } = Typography;

interface Token {
  id: number;
  name: string;
  app_name: string | null;
  app_version: string | null;
  scope: string;
  permissions: {
    read_samples: boolean;
    write_samples: boolean;
    recognize: boolean;
    read_users: boolean;
    manage_users: boolean;
    manage_schools: boolean;
    manage_training: boolean;
    manage_system: boolean;
  };
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  usage_count: number;
}

interface CreatedToken {
  id: number;
  name: string;
  token: string;
  scope: string;
  permissions: any;
  created_at: string;
  expires_at: string | null;
  message: string;
}

const TokenManagement: React.FC = () => {
  const [form] = Form.useForm();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createdToken, setCreatedToken] = useState<CreatedToken | null>(null);
  const [selectedScope, setSelectedScope] = useState('read');
  const [showFullToken, setShowFullToken] = useState(false);
  const [expirationType, setExpirationType] = useState('30d');
  const [customExpiresAt, setCustomExpiresAt] = useState<Dayjs | null>(null);
  const [showWarning, setShowWarning] = useState(false);
  const [confirmedRisk, setConfirmedRisk] = useState(false);

  const queryClient = useQueryClient();

  // Fetch tokens
  const { data: tokensData, isLoading, error } = useQuery({
    queryKey: ['tokens'],
    queryFn: async () => {
      const res = await api.get('/tokens/list');
      return res.data;
    }
  });

  // Create token mutation
  const createMutation = useMutation({
    mutationFn: async (values: any) => {
      const res = await api.post('/tokens/create', values);
      return res.data;
    },
    onSuccess: (data) => {
      message.success('API Token 创建成功');
      setCreatedToken(data);
      setCreateModalVisible(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || '创建失败');
    }
  });

  // Delete token mutation
  const deleteMutation = useMutation({
    mutationFn: async (token_id: number) => {
      await api.delete(`/tokens/${token_id}`);
    },
    onSuccess: () => {
      message.success('Token 删除成功');
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || '删除失败');
    }
  });

  // Revoke token mutation
  const revokeMutation = useMutation({
    mutationFn: async (token_id: number) => {
      await api.post(`/tokens/${token_id}/revoke`);
    },
    onSuccess: () => {
      message.success('Token 撤销成功');
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || '撤销失败');
    }
  });

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const permissions = [];
      if (values.read_samples) permissions.push('read_samples');
      if (values.write_samples) permissions.push('write_samples');
      if (values.recognize) permissions.push('recognize');
      if (values.read_users) permissions.push('read_users');
      if (values.manage_users) permissions.push('manage_users');
      if (values.manage_schools) permissions.push('manage_schools');
      if (values.manage_training) permissions.push('manage_training');
      if (values.manage_system) permissions.push('manage_system');

      // Check if confirmation is needed
      if (showWarning && !confirmedRisk) {
        message.warning('请先确认创建高风险 Token 的操作');
        return;
      }

      const payload: any = {
        ...values,
        permissions,
        expiration_type: expirationType,
        confirmed: confirmedRisk
      };

      if (expirationType === 'custom' && customExpiresAt) {
        payload.custom_expires_at = customExpiresAt.toISOString();
      }

      createMutation.mutate(payload);
    });
  };

  const handleDelete = (token_id: number) => {
    deleteMutation.mutate(token_id);
  };

  const handleRevoke = (token_id: number) => {
    revokeMutation.mutate(token_id);
  };

  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    message.success('Token 已复制到剪贴板');
  };

  const maskToken = (token: string) => {
    if (showFullToken) return token;
    return `${token.substring(0, 8)}...${token.substring(token.length - 4)}`;
  };

  const columns = [
    {
      title: 'Token 名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Token) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          {record.app_name && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.app_name} {record.app_version && `v${record.app_version}`}
            </Text>
          )}
        </Space>
      )
    },
    {
      title: '作用域',
      dataIndex: 'scope',
      key: 'scope',
      width: 100,
      render: (scope: string) => {
        const colors = {
          read: 'blue',
          write: 'green',
          admin: 'red'
        };
        return <Tag color={colors[scope as keyof typeof colors]}>{scope.toUpperCase()}</Tag>;
      }
    },
    {
      title: '权限',
      key: 'permissions',
      width: 200,
      render: (_: any, record: Token) => (
        <Space size={[4, 4]} wrap>
          {record.permissions.read_samples && <Tag color="blue">读取样本</Tag>}
          {record.permissions.write_samples && <Tag color="green">写入样本</Tag>}
          {record.permissions.recognize && <Tag color="orange">识别</Tag>}
          {record.permissions.read_users && <Tag color="cyan">读取用户</Tag>}
          {record.permissions.manage_users && <Tag color="red">管理用户</Tag>}
          {record.permissions.manage_schools && <Tag color="purple">管理学校</Tag>}
          {record.permissions.manage_training && <Tag color="volcano">训练管理</Tag>}
          {record.permissions.manage_system && <Tag color="magenta">系统管理</Tag>}
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <Tag
          icon={active ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
          color={active ? 'success' : 'error'}
        >
          {active ? '活跃' : '已撤销'}
        </Tag>
      )
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      render: (count: number) => <Text>{count}</Text>
    },
    {
      title: '最后使用',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 150,
      render: (date: string | null) => (
        <Text type="secondary">
          {formatDateToLocal(date) || '从未使用'}
        </Text>
      )
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 150,
      render: (date: string | null, record: Token) => {
        if (!date && record.is_active) {
          return <Tag color="red">永不过期</Tag>;
        } else if (!date) {
          return <Text type="secondary">-</Text>;
        }
        
        // Parse as UTC to avoid timezone issues
        const expiryDate = dayjs.utc(date);
        const now = dayjs.utc();
        const daysLeft = expiryDate.diff(now, 'days');

        let color = 'default';
        if (daysLeft <= 0) color = 'red';
        else if (daysLeft <= 7) color = 'orange';
        else if (daysLeft <= 30) color = 'gold';
        else if (daysLeft <= 90) color = 'blue';

        return (
          <Tag color={color}>
            {daysLeft <= 0 ? '已过期' : `${daysLeft}天后过期`}
          </Tag>
        );
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => (
        <Text type="secondary">{formatDateToLocal(date)}</Text>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: Token) => (
        <Space size="small">
          {record.is_active ? (
            <Popconfirm
              title="确定要撤销此 Token 吗？"
              description="撤销后 Token 将无法使用，但可以被重新激活"
              onConfirm={() => handleRevoke(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="撤销 Token">
                <Button type="link" size="small" icon={<StopOutlined />}>
                  撤销
                </Button>
              </Tooltip>
            </Popconfirm>
          ) : (
            <Tooltip title="已撤销，无法使用">
              <Button type="link" size="small" disabled icon={<StopOutlined />}>
                已撤销
              </Button>
            </Tooltip>
          )}
          <Popconfirm
            title="确定要删除此 Token 吗？"
            description="删除后无法恢复，请确认"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除 Token">
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const getPermissionsForScope = (scope: string) => {
    if (scope === 'read') {
      return {
        read_samples: true,
        write_samples: false,
        recognize: false,
        read_users: true,
        manage_users: false,
        manage_schools: false,
        manage_training: false,
        manage_system: false
      };
    } else if (scope === 'write') {
      return {
        read_samples: true,
        write_samples: true,
        recognize: true,
        read_users: true,
        manage_users: false,
        manage_schools: false,
        manage_training: false,
        manage_system: false
      };
    } else if (scope === 'admin') {
      return {
        read_samples: true,
        write_samples: true,
        recognize: true,
        read_users: true,
        manage_users: true,
        manage_schools: true,
        manage_training: true,
        manage_system: true
      };
    }
    return {
      read_samples: false,
      write_samples: false,
      recognize: false,
      read_users: false,
      manage_users: false,
      manage_schools: false,
      manage_training: false,
      manage_system: false
    };
  };

  useEffect(() => {
    const perms = getPermissionsForScope(selectedScope);
    form.setFieldsValue(perms);
  }, [selectedScope, form]);

  // Check if warning should be shown based on expiration type
  useEffect(() => {
    if (expirationType === 'never') {
      setShowWarning(true);
      setConfirmedRisk(false);
    } else if (expirationType === 'custom' && customExpiresAt) {
      const days = customExpiresAt.diff(dayjs(), 'days');
      if (days > 90) {
        setShowWarning(true);
        setConfirmedRisk(false);
      } else {
        setShowWarning(false);
      }
    } else {
      setShowWarning(false);
      setConfirmedRisk(false);
    }
  }, [expirationType, customExpiresAt]);

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <KeyOutlined /> API Token 管理
      </Title>
      <Paragraph type="secondary">
        管理用于外部应用集成的 API Token。创建 Token 后请妥善保管，它只会显示一次。
      </Paragraph>

      <Tabs
        defaultActiveKey="tokens"
        items={[
          {
            key: 'tokens',
            label: (
              <span>
                <AppstoreOutlined />
                Token 列表
              </span>
            ),
            children: (
              <Card>
                <Space style={{ marginBottom: '16px' }}>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setCreateModalVisible(true)}
                  >
                    创建 Token
                  </Button>
                </Space>

                <Table
                  columns={columns}
                  dataSource={tokensData?.tokens || []}
                  rowKey="id"
                  loading={isLoading}
                  scroll={{ x: 1200 }}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 个 Token`
                  }}
                />
              </Card>
            )
          },
          {
            key: 'api-test',
            label: (
              <span>
                <ApiOutlined />
                API 测试
              </span>
            ),
            children: <TokenAPITest />
          }
        ]}
      />

      {/* Create Token Modal */}
      <Modal
        title="创建 API Token"
        open={createModalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
          setExpirationType('30d');
          setCustomExpiresAt(null);
          setShowWarning(false);
          setConfirmedRisk(false);
        }}
        confirmLoading={createMutation.isPending}
        width={700}
        okButtonProps={{ disabled: showWarning && !confirmedRisk }}
      >
        <Alert
          message="安全提示"
          description="Token 创建成功后将只显示一次，请务必保存到安全的地方。泄露 Token 可能导致安全风险。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {showWarning && (
          <Alert
            message="安全警告"
            description={
              expirationType === 'never'
                ? '您正在创建一个永不过期的 Token。如果此 Token 泄露，将带来永久的安全风险。请确认您了解此风险。'
                : '您设置的 Token 过期时间超过 90 天。长时间的有效期会增加安全风险，请确认您了解此风险。'
            }
            type="error"
            showIcon
            closable={false}
            style={{ marginBottom: 16 }}
          />
        )}

        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Token 名称"
            rules={[{ required: true, message: '请输入 Token 名称' }]}
          >
            <Input placeholder="例如：教学平台集成 Token" />
          </Form.Item>

          <Form.Item name="app_name" label="应用名称">
            <Input placeholder="例如：My Learning App" />
          </Form.Item>

          <Form.Item name="app_version" label="应用版本">
            <Input placeholder="例如：1.0.0" />
          </Form.Item>

          <Form.Item
            name="scope"
            label="Token 作用域"
            rules={[{ required: true, message: '请选择作用域' }]}
          >
            <Select
              value={selectedScope}
              onChange={(value) => setSelectedScope(value)}
            >
              <Select.Option value="read">只读 (read)</Select.Option>
              <Select.Option value="write">读写 (write)</Select.Option>
              <Select.Option value="admin">管理员 (admin)</Select.Option>
            </Select>
          </Form.Item>

          <Divider orientation="left">过期时间设置</Divider>

          <Form.Item label="过期时间">
            <Radio.Group
              value={expirationType}
              onChange={(e) => setExpirationType(e.target.value)}
            >
              <Space direction="vertical">
                <Radio value="1d">1 天</Radio>
                <Radio value="7d">7 天</Radio>
                <Radio value="30d">30 天（推荐）</Radio>
                <Radio value="90d">90 天</Radio>
                <Radio value="never">
                  <Text type={expirationType === 'never' ? 'danger' : undefined}>
                    永不过期
                  </Text>
                </Radio>
                <Radio value="custom">
                  自定义过期时间
                </Radio>
              </Space>
            </Radio.Group>
          </Form.Item>

          {expirationType === 'custom' && (
            <Form.Item
              name="custom_expires_at"
              label="选择过期时间"
              rules={[{ required: true, message: '请选择过期时间' }]}
            >
              <DatePicker
                showTime
                style={{ width: '100%' }}
                placeholder="选择过期日期和时间"
                disabledDate={(current) => {
                  // Can't select past dates
                  return current && current < dayjs().startOf('day');
                }}
                onChange={(date) => setCustomExpiresAt(date)}
                value={customExpiresAt}
              />
            </Form.Item>
          )}

          {showWarning && (
            <Form.Item>
              <Checkbox
                checked={confirmedRisk}
                onChange={(e) => setConfirmedRisk(e.target.checked)}
              >
                <Text type="danger">
                  我已了解并接受创建 {expirationType === 'never' ? '永不过期的 Token' : '过期时间超过 90 天的 Token'} 可能带来的安全风险
                </Text>
              </Checkbox>
            </Form.Item>
          )}

          <Divider>权限配置</Divider>

          <Form.Item name="read_samples" valuePropName="checked">
            <Checkbox>读取样本 - 可以查看和列出样本</Checkbox>
          </Form.Item>

          <Form.Item name="write_samples" valuePropName="checked">
            <Checkbox>写入样本 - 可以上传样本</Checkbox>
          </Form.Item>

          <Form.Item name="recognize" valuePropName="checked">
            <Checkbox>识别 - 可以执行字迹识别</Checkbox>
          </Form.Item>

          <Form.Item name="read_users" valuePropName="checked">
            <Checkbox>读取用户 - 可以查看用户信息</Checkbox>
          </Form.Item>

          <Form.Item name="manage_users" valuePropName="checked">
            <Checkbox>管理用户 - 可以创建、修改和删除用户</Checkbox>
          </Form.Item>

          <Form.Item name="manage_schools" valuePropName="checked">
            <Checkbox>管理学校 - 可以创建、修改和删除学校</Checkbox>
          </Form.Item>

          <Form.Item name="manage_training" valuePropName="checked">
            <Checkbox>训练管理 - 可以管理模型训练</Checkbox>
          </Form.Item>

          <Form.Item name="manage_system" valuePropName="checked">
            <Checkbox>系统管理 - 可以重载系统配置和管理配额限制</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      {/* Token Created Modal */}
      <Modal
        title={<><CheckCircleOutlined style={{ color: '#52c41a' }} /> Token 创建成功</>}
        open={!!createdToken}
        onOk={() => setCreatedToken(null)}
        onCancel={() => setCreatedToken(null)}
        okText="我已保存"
        width={700}
        footer={[
          <Button key="close" type="primary" onClick={() => setCreatedToken(null)}>
            我已保存 Token
          </Button>
        ]}
      >
        <Alert
          message="重要提示"
          description="此 Token 只会显示这一次，请立即保存到安全的地方！如果丢失，需要重新创建新的 Token。"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Descriptions bordered column={1}>
          <Descriptions.Item label="Token 名称">
            {createdToken?.name}
          </Descriptions.Item>
          <Descriptions.Item label="API Token">
            <Space>
              <Text
                code
                copyable={{ text: createdToken?.token }}
                style={{ fontSize: '14px', fontFamily: 'monospace' }}
              >
                {maskToken(createdToken?.token || '')}
              </Text>
              <Tooltip title={showFullToken ? '隐藏' : '显示'}>
                <Button
                  type="link"
                  size="small"
                  icon={showFullToken ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                  onClick={() => setShowFullToken(!showFullToken)}
                />
              </Tooltip>
              <Button
                type="link"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => copyToken(createdToken?.token || '')}
              >
                复制
              </Button>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="作用域">
            <Tag color="blue">{createdToken?.scope?.toUpperCase()}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="过期时间">
            {!createdToken?.expires_at ? (
              <Tag color="red">永不过期</Tag>
            ) : (
              <Text>{formatDateToLocal(createdToken.expires_at)}</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {createdToken?.created_at ? formatDateToLocal(createdToken.created_at) : '-'}
          </Descriptions.Item>
        </Descriptions>

        <Alert
          message="使用方法"
          description={
            <div>
              <Paragraph code copyable>
                Authorization: Bearer {createdToken?.token}
              </Paragraph>
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                在所有 API 请求的 Header 中添加上述 Authorization 字段即可使用此 Token。
              </Paragraph>
            </div>
          }
          type="info"
          showIcon
          style={{ marginTop: 16 }}
        />
      </Modal>
    </div>
  );
};

export default TokenManagement;
