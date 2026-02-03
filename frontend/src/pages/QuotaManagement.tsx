import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  InputNumber,
  Input,
  Select,
  message,
  Space,
  Tooltip,
  Tag,
  Card,
  Descriptions,
  Drawer,
  Statistic,
  Row,
  Col,
  Popconfirm
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  UserOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { api } from '../services/api';

interface Quota {
  id: number;
  quota_type: 'user' | 'school';
  user_id?: number;
  school_id?: number;
  minute_limit: number;
  hour_limit: number;
  day_limit: number;
  month_limit: number;
  total_limit: number;
  minute_used: number;
  hour_used: number;
  day_used: number;
  month_used: number;
  total_used: number;
  description?: string;
  created_at: string;
  updated_at?: string;
}

interface User {
  id: number;
  username: string;
  nickname?: string;
  role: string;
  school_id?: number;
}

interface School {
  id: number;
  name: string;
}

const QuotaManagement: React.FC = () => {
  const [quotas, setQuotas] = useState<Quota[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingQuota, setEditingQuota] = useState<Quota | null>(null);
  const [selectedQuota, setSelectedQuota] = useState<Quota | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [userRole, setUserRole] = useState<string>('');
  const [schoolId, setSchoolId] = useState<number | undefined>(undefined);
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);

  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();

  useEffect(() => {
    fetchQuotas();
    fetchUsers();
    fetchSchools();
    loadUserRole();
  }, []);

  const loadUserRole = async () => {
    try {
      const response = await api.get('/auth/me');
      setUserRole(response.data.role);
      setSchoolId(response.data.school_id);
    } catch (error) {
      console.error('Failed to load user role:', error);
    }
  };

  const fetchQuotas = async () => {
    setLoading(true);
    try {
      const response = await api.get('/quotas');
      setQuotas(response.data);
    } catch (error) {
      message.error('获取配额列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users');
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchSchools = async () => {
    try {
      const response = await api.get('/schools');
      setSchools(response.data);
    } catch (error) {
      console.error('Failed to fetch schools:', error);
    }
  };

  const fetchLogs = async (quotaId: number) => {
    setLogsLoading(true);
    try {
      const response = await api.get(`/quotas/${quotaId}/logs?limit=50`);
      setLogs(response.data);
    } catch (error) {
      message.error('获取日志失败');
    } finally {
      setLogsLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingQuota(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (quota: Quota) => {
    setEditingQuota(quota);
    form.setFieldsValue({
      ...quota,
      user_id: quota.user_id,
      school_id: quota.school_id
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/quotas/${id}`);
      message.success('删除成功');
      fetchQuotas();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingQuota) {
        await api.put(`/quotas/${editingQuota.id}`, values);
        message.success('更新成功');
      } else {
        await api.post('/quotas', values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchQuotas();
    } catch (error: any) {
      if (error.response?.status === 429) {
        message.error('配额更新受限');
      } else {
        message.error(editingQuota ? '更新失败' : '创建失败');
      }
    }
  };

  const handleBatchUpdate = async () => {
    try {
      const values = await batchForm.validateFields();
      await api.post('/quotas/batch-update', {
        ...values,
        user_ids: selectedUserIds
      });
      message.success(`成功更新 ${selectedUserIds.length} 个用户配额`);
      setBatchModalVisible(false);
      batchForm.resetFields();
      setSelectedUserIds([]);
      fetchQuotas();
    } catch (error: any) {
      message.error('批量更新失败');
    }
  };

  const handleReset = async (quotaId: number) => {
    try {
      await api.post(`/quotas/${quotaId}/reset`, { reset_type: 'all' });
      message.success('重置成功');
      fetchQuotas();
    } catch (error) {
      message.error('重置失败');
    }
  };

  const handleViewLogs = (quota: Quota) => {
    setSelectedQuota(quota);
    setDrawerVisible(true);
    fetchLogs(quota.id);
  };

  const getUserName = (userId?: number) => {
    const user = users.find(u => u.id === userId);
    return user ? user.nickname || user.username : '-';
  };

  const getSchoolName = (schoolId?: number) => {
    const school = schools.find(s => s.id === schoolId);
    return school ? school.name : '-';
  };

  const getUsagePercentage = (used: number, limit: number) => {
    if (limit === 0) return 0;
    return Math.round((used / limit) * 100);
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80
    },
    {
      title: '类型',
      dataIndex: 'quota_type',
      key: 'quota_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'user' ? 'blue' : 'green'}>
          {type === 'user' ? <UserOutlined /> : <TeamOutlined />}
          {type === 'user' ? '用户' : '学校'}
        </Tag>
      )
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
      render: (userId: number | undefined) => (
        <span>{getUserName(userId)}</span>
      )
    },
    {
      title: '学校',
      dataIndex: 'school_id',
      key: 'school_id',
      width: 150,
      render: (schoolId: number | undefined) => (
        <span>{getSchoolName(schoolId)}</span>
      )
    },
    {
      title: '每分钟',
      key: 'minute',
      width: 120,
      render: (_: any, record: Quota) => {
        const percentage = getUsagePercentage(record.minute_used, record.minute_limit);
        return (
          <div>
            <div>{record.minute_used} / {record.minute_limit || '∞'}</div>
            {percentage > 80 && percentage <= 100 && <Tag color="orange">警告</Tag>}
            {percentage > 100 && <Tag color="red">超限</Tag>}
          </div>
        );
      }
    },
    {
      title: '每小时',
      key: 'hour',
      width: 120,
      render: (_: any, record: Quota) => {
        const percentage = getUsagePercentage(record.hour_used, record.hour_limit);
        return (
          <div>
            <div>{record.hour_used} / {record.hour_limit || '∞'}</div>
            {percentage > 80 && percentage <= 100 && <Tag color="orange">警告</Tag>}
            {percentage > 100 && <Tag color="red">超限</Tag>}
          </div>
        );
      }
    },
    {
      title: '每天',
      key: 'day',
      width: 120,
      render: (_: any, record: Quota) => {
        const percentage = getUsagePercentage(record.day_used, record.day_limit);
        return (
          <div>
            <div>{record.day_used} / {record.day_limit || '∞'}</div>
            {percentage > 80 && percentage <= 100 && <Tag color="orange">警告</Tag>}
            {percentage > 100 && <Tag color="red">超限</Tag>}
          </div>
        );
      }
    },
    {
      title: '每月',
      key: 'month',
      width: 120,
      render: (_: any, record: Quota) => {
        const percentage = getUsagePercentage(record.month_used, record.month_limit);
        return (
          <div>
            <div>{record.month_used} / {record.month_limit || '∞'}</div>
            {percentage > 80 && percentage <= 100 && <Tag color="orange">警告</Tag>}
            {percentage > 100 && <Tag color="red">超限</Tag>}
          </div>
        );
      }
    },
    {
      title: '总计',
      key: 'total',
      width: 120,
      render: (_: any, record: Quota) => {
        const percentage = getUsagePercentage(record.total_used, record.total_limit);
        return (
          <div>
            <div>{record.total_used} / {record.total_limit || '∞'}</div>
            {percentage > 80 && percentage <= 100 && <Tag color="orange">警告</Tag>}
            {percentage > 100 && <Tag color="red">超限</Tag>}
          </div>
        );
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: Quota) => (
        <Space size="small">
          <Tooltip title="查看日志">
            <Button
              type="link"
              icon={<ClockCircleOutlined />}
              onClick={() => handleViewLogs(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="重置">
            <Button
              type="link"
              icon={<ReloadOutlined />}
              onClick={() => handleReset(record.id)}
            />
          </Tooltip>
          {(userRole === 'system_admin' || userRole === 'school_admin') && (
            <Popconfirm
              title="确定要删除该配额吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          )}
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>配额管理</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchQuotas}>
              刷新
            </Button>
            {(userRole === 'system_admin' || userRole === 'school_admin') && (
              <>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                >
                  新建配额
                </Button>
                <Button
                  icon={<SettingOutlined />}
                  onClick={() => setBatchModalVisible(true)}
                >
                  批量设置
                </Button>
              </>
            )}
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={quotas}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      {/* 新建/编辑配额弹窗 */}
      <Modal
        title={editingQuota ? '编辑配额' : '新建配额'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
        okText="确定"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="配额类型"
            name="quota_type"
            rules={[{ required: true, message: '请选择配额类型' }]}
          >
            <Select placeholder="请选择配额类型">
              <Select.Option value="user">用户配额</Select.Option>
              {(userRole === 'system_admin') && (
                <Select.Option value="school">学校配额</Select.Option>
              )}
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.quota_type !== currentValues.quota_type
            }
          >
            {({ getFieldValue }) => {
              const quotaType = getFieldValue('quota_type');
              return (
                <>
                  {quotaType === 'user' && (
                    <Form.Item
                      label="用户"
                      name="user_id"
                      rules={[{ required: true, message: '请选择用户' }]}
                    >
                      <Select
                        showSearch
                        placeholder="请选择用户"
                        filterOption={(input, option) =>
                          String(option?.children || '')
                            .toLowerCase()
                            .includes(input.toLowerCase())
                        }
                      >
                        {users
                          .filter(
                            user =>
                              userRole === 'system_admin' ||
                              user.school_id === schoolId
                          )
                          .map(user => (
                            <Select.Option key={user.id} value={user.id}>
                              {user.nickname || user.username} ({user.role})
                            </Select.Option>
                          ))}
                      </Select>
                    </Form.Item>
                  )}

                  {quotaType === 'school' && (
                    <Form.Item
                      label="学校"
                      name="school_id"
                      rules={[{ required: true, message: '请选择学校' }]}
                    >
                      <Select
                        showSearch
                        placeholder="请选择学校"
                        filterOption={(input, option) =>
                          String(option?.children || '')
                            .toLowerCase()
                            .includes(input.toLowerCase())
                        }
                      >
                        {schools.map(school => (
                          <Select.Option key={school.id} value={school.id}>
                            {school.name}
                          </Select.Option>
                        ))}
                      </Select>
                    </Form.Item>
                  )}
                </>
              );
            }}
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="每分钟限制"
                name="minute_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="每小时限制"
                name="hour_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="每天限制"
                name="day_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="每月限制"
                name="month_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="总次数限制" name="total_limit" initialValue={0}>
            <Space.Compact style={{ width: '100%' }}>
              <InputNumber min={0} style={{ width: '100%' }} />
              <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
            </Space.Compact>
          </Form.Item>

          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入配额描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量设置弹窗 */}
      <Modal
        title="批量设置用户配额"
        open={batchModalVisible}
        onOk={handleBatchUpdate}
        onCancel={() => setBatchModalVisible(false)}
        width={600}
        okText="确定"
        cancelText="取消"
      >
        <Form form={batchForm} layout="vertical">
          <Form.Item
            label="选择用户"
            name="user_ids"
            rules={[{ required: true, message: '请选择用户' }]}
          >
            <Select
              mode="multiple"
              showSearch
              placeholder="请选择用户"
              onChange={(values) => setSelectedUserIds(values)}
              filterOption={(input, option) =>
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {users
                .filter(
                  user =>
                    userRole === 'system_admin' ||
                    user.school_id === schoolId
                )
                .map(user => (
                  <Select.Option key={user.id} value={user.id}>
                    {user.nickname || user.username} ({user.role})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="每分钟限制"
                name="minute_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="每小时限制"
                name="hour_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="每天限制"
                name="day_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="每月限制"
                name="month_limit"
                initialValue={0}
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                  <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
                </Space.Compact>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="总次数限制" name="total_limit" initialValue={0}>
            <Space.Compact style={{ width: '100%' }}>
              <InputNumber min={0} style={{ width: '100%' }} />
              <Input disabled defaultValue="次" style={{ width: '60px', textAlign: 'center' }} />
            </Space.Compact>
          </Form.Item>

          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入配额描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 配额详情抽屉 */}
      <Drawer
        title="配额详情"
        placement="right"
        width={800}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedQuota && (
          <div>
            <Card title="配额信息" style={{ marginBottom: 16 }}>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="ID">
                  {selectedQuota.id}
                </Descriptions.Item>
                <Descriptions.Item label="类型">
                  <Tag color={selectedQuota.quota_type === 'user' ? 'blue' : 'green'}>
                    {selectedQuota.quota_type === 'user' ? '用户' : '学校'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="用户">
                  {getUserName(selectedQuota.user_id)}
                </Descriptions.Item>
                <Descriptions.Item label="学校">
                  {getSchoolName(selectedQuota.school_id)}
                </Descriptions.Item>
                <Descriptions.Item label="描述" span={2}>
                  {selectedQuota.description || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="使用统计" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="每分钟"
                    value={selectedQuota.minute_used}
                    suffix={`/ ${selectedQuota.minute_limit || '∞'}`}
                    valueStyle={{
                      color:
                        selectedQuota.minute_limit > 0 &&
                        selectedQuota.minute_used >= selectedQuota.minute_limit
                          ? '#cf1322'
                          : '#3f8600'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="每小时"
                    value={selectedQuota.hour_used}
                    suffix={`/ ${selectedQuota.hour_limit || '∞'}`}
                    valueStyle={{
                      color:
                        selectedQuota.hour_limit > 0 &&
                        selectedQuota.hour_used >= selectedQuota.hour_limit
                          ? '#cf1322'
                          : '#3f8600'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="每天"
                    value={selectedQuota.day_used}
                    suffix={`/ ${selectedQuota.day_limit || '∞'}`}
                    valueStyle={{
                      color:
                        selectedQuota.day_limit > 0 &&
                        selectedQuota.day_used >= selectedQuota.day_limit
                          ? '#cf1322'
                          : '#3f8600'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="每月"
                    value={selectedQuota.month_used}
                    suffix={`/ ${selectedQuota.month_limit || '∞'}`}
                    valueStyle={{
                      color:
                        selectedQuota.month_limit > 0 &&
                        selectedQuota.month_used >= selectedQuota.month_limit
                          ? '#cf1322'
                          : '#3f8600'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="总计"
                    value={selectedQuota.total_used}
                    suffix={`/ ${selectedQuota.total_limit || '∞'}`}
                    valueStyle={{
                      color:
                        selectedQuota.total_limit > 0 &&
                        selectedQuota.total_used >= selectedQuota.total_limit
                          ? '#cf1322'
                          : '#3f8600'
                    }}
                  />
                </Col>
              </Row>
            </Card>

            <Card title="使用日志">
              <Table
                columns={[
                  {
                    title: '时间',
                    dataIndex: 'created_at',
                    key: 'created_at',
                    render: (date: string) =>
                      new Date(date).toLocaleString('zh-CN')
                  },
                  {
                    title: '是否允许',
                    dataIndex: 'is_allowed',
                    key: 'is_allowed',
                    render: (allowed: boolean) => (
                      <Tag color={allowed ? 'green' : 'red'}>
                        {allowed ? '允许' : '拒绝'}
                      </Tag>
                    )
                  },
                  {
                    title: '拒绝原因',
                    dataIndex: 'deny_reason',
                    key: 'deny_reason',
                    render: (reason: string) => reason || '-'
                  }
                ]}
                dataSource={logs}
                rowKey="id"
                loading={logsLoading}
                pagination={{ pageSize: 10 }}
                size="small"
              />
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default QuotaManagement;
