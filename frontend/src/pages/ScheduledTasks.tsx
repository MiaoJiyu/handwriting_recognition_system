import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Switch,
  Space,
  Tag,
  Tooltip,
  Popconfirm,
  Card,
  Row,
  Col,
  Statistic,
  message,
  Timeline,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

const { TextArea } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface ScheduledTask {
  id: number;
  name: string;
  description?: string;
  status: string;
  trigger_type: string;
  interval_seconds?: number;
  cron_expression?: string;
  run_at?: string;
  training_mode: string;
  school_id?: number;
  school_name?: string;
  force_retrain: boolean;
  last_run_at?: string;
  next_run_at?: string;
  total_runs: number;
  success_runs: number;
  failed_runs: number;
  last_error?: string;
  created_by: number;
  creator_name?: string;
  created_at: string;
  updated_at: string;
}

interface ScheduledTaskExecution {
  id: number;
  scheduled_task_id: number;
  training_job_id?: number;
  started_at: string;
  completed_at?: string;
  status: string;
  output?: string;
  error_message?: string;
}

const ScheduledTasks = () => {
  const [form] = Form.useForm();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const [selectedTask, setSelectedTask] = useState<ScheduledTask | null>(null);
  const [isHistoryModalVisible, setIsHistoryModalVisible] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterMode, setFilterMode] = useState<string | undefined>();
  const [triggerType, setTriggerType] = useState<string>('interval');

  const queryClient = useQueryClient();

  // Fetch scheduled tasks
  const { data: tasks, isLoading } = useQuery<ScheduledTask[]>({
    queryKey: ['scheduledTasks', filterStatus, filterMode],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filterStatus) params.append('status', filterStatus);
      if (filterMode) params.append('training_mode', filterMode);
      const response = await api.get(`/scheduled-tasks?${params.toString()}`);
      return response.data;
    },
  });

  // Fetch schools
  const { data: schools } = useQuery<{ id: number; name: string }[]>({
    queryKey: ['schools'],
    queryFn: async () => {
      const response = await api.get('/schools');
      return response.data;
    },
  });

  // Fetch task executions
  const { data: executions = [] } = useQuery<ScheduledTaskExecution[]>({
    queryKey: ['taskExecutions', selectedTask?.id],
    queryFn: async () => {
      if (!selectedTask) return [];
      const response = await api.get(`/scheduled-tasks/${selectedTask.id}/executions`);
      return response.data;
    },
    enabled: !!selectedTask && isHistoryModalVisible,
  });

  // Create task mutation
  const createTaskMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/scheduled-tasks', data);
      return response.data;
    },
    onSuccess: () => {
      message.success('定时任务创建成功');
      setIsModalVisible(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['scheduledTasks'] });
    },
    onError: (error: any) => {
      message.error(`创建失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Update task mutation
  const updateTaskMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => {
      const response = await api.put(`/scheduled-tasks/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      message.success('定时任务更新成功');
      setIsModalVisible(false);
      form.resetFields();
      setEditingTask(null);
      queryClient.invalidateQueries({ queryKey: ['scheduledTasks'] });
    },
    onError: (error: any) => {
      message.error(`更新失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete task mutation
  const deleteTaskMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/scheduled-tasks/${id}`);
    },
    onSuccess: () => {
      message.success('定时任务删除成功');
      queryClient.invalidateQueries({ queryKey: ['scheduledTasks'] });
    },
    onError: (error: any) => {
      message.error(`删除失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Pause task mutation
  const pauseTaskMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post(`/scheduled-tasks/${id}/pause`);
      return response.data;
    },
    onSuccess: () => {
      message.success('任务已暂停');
      queryClient.invalidateQueries({ queryKey: ['scheduledTasks'] });
    },
    onError: (error: any) => {
      message.error(`暂停失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Resume task mutation
  const resumeTaskMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post(`/scheduled-tasks/${id}/resume`);
      return response.data;
    },
    onSuccess: () => {
      message.success('任务已恢复');
      queryClient.invalidateQueries({ queryKey: ['scheduledTasks'] });
    },
    onError: (error: any) => {
      message.error(`恢复失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleCreate = () => {
    setEditingTask(null);
    form.resetFields();
    form.setFieldsValue({ trigger_type: 'interval', training_mode: 'full' });
    setTriggerType('interval');
    setIsModalVisible(true);
  };

  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task);
    form.setFieldsValue({
      ...task,
      trigger_type: task.trigger_type,
      training_mode: task.training_mode,
    });
    setTriggerType(task.trigger_type);
    setIsModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // 转换触发器配置
      if (values.trigger_type === 'once') {
        if (values.run_at) {
          values.run_at = values.run_at.toISOString();
        }
      }

      if (editingTask) {
        updateTaskMutation.mutate({ id: editingTask.id, data: values });
      } else {
        createTaskMutation.mutate(values);
      }
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  const handleDelete = (id: number) => {
    deleteTaskMutation.mutate(id);
  };

  const handlePause = (id: number) => {
    pauseTaskMutation.mutate(id);
  };

  const handleResume = (id: number) => {
    resumeTaskMutation.mutate(id);
  };

  const handleViewHistory = (task: ScheduledTask) => {
    setSelectedTask(task);
    setIsHistoryModalVisible(true);
  };

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      active: { color: 'green', text: '活跃' },
      paused: { color: 'orange', text: '暂停' },
      completed: { color: 'blue', text: '完成' },
      failed: { color: 'red', text: '失败' },
    };
    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getTriggerDescription = (task: ScheduledTask) => {
    switch (task.trigger_type) {
      case 'once':
        return `一次性: ${task.run_at ? new Date(task.run_at).toLocaleString('zh-CN') : '未设置'}`;
      case 'interval':
        return `间隔: ${task.interval_seconds ? `${task.interval_seconds}秒` : '未设置'}`;
      case 'cron':
        return `Cron: ${task.cron_expression || '未设置'}`;
      default:
        return '未知';
    }
  };

  const getExecutionStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 150,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '触发方式',
      key: 'trigger',
      width: 200,
      render: (_: any, record: ScheduledTask) => getTriggerDescription(record),
    },
    {
      title: '训练模式',
      dataIndex: 'training_mode',
      key: 'training_mode',
      width: 100,
      render: (mode: string) => (
        <Tag color={mode === 'full' ? 'blue' : 'purple'}>
          {mode === 'full' ? '全量' : '增量'}
        </Tag>
      ),
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 120,
      render: (name: string) => name || '全校',
    },
    {
      title: '执行统计',
      key: 'stats',
      width: 150,
      render: (_: any, record: ScheduledTask) => (
        <Space direction="vertical" size="small">
          <span>总: {record.total_runs}</span>
          <span style={{ color: '#52c41a' }}>成功: {record.success_runs}</span>
          <span style={{ color: '#ff4d4f' }}>失败: {record.failed_runs}</span>
        </Space>
      ),
    },
    {
      title: '下次执行',
      dataIndex: 'next_run_at',
      key: 'next_run_at',
      width: 180,
      render: (date: string) => {
        if (!date) return '-';
        return new Date(date).toLocaleString('zh-CN');
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: ScheduledTask) => (
        <Space size="small">
          <Tooltip title="查看历史">
            <Button
              type="link"
              size="small"
              icon={<HistoryOutlined />}
              onClick={() => handleViewHistory(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          {record.status === 'active' ? (
            <Tooltip title="暂停">
              <Button
                type="link"
                size="small"
                icon={<PauseCircleOutlined />}
                onClick={() => handlePause(record.id)}
              />
            </Tooltip>
          ) : (
            <Tooltip title="恢复">
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleResume(record.id)}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="确认删除?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃任务"
              value={tasks?.filter(t => t.status === 'active').length || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="暂停任务"
              value={tasks?.filter(t => t.status === 'paused').length || 0}
              prefix={<PauseCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总执行次数"
              value={tasks?.reduce((sum, t) => sum + t.total_runs, 0) || 0}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功次数"
              value={tasks?.reduce((sum, t) => sum + t.success_runs, 0) || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="定时任务管理"
        extra={
          <Space>
            <Select
              placeholder="状态筛选"
              style={{ width: 120 }}
              allowClear
              onChange={setFilterStatus}
            >
              <Option value="active">活跃</Option>
              <Option value="paused">暂停</Option>
              <Option value="completed">完成</Option>
              <Option value="failed">失败</Option>
            </Select>
            <Select
              placeholder="模式筛选"
              style={{ width: 120 }}
              allowClear
              onChange={setFilterMode}
            >
              <Option value="full">全量训练</Option>
              <Option value="incremental">增量训练</Option>
            </Select>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              创建任务
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tasks}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1400 }}
        />
      </Card>

      <Modal
        title={editingTask ? '编辑定时任务' : '创建定时任务'}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
        width={600}
        okText="确定"
        cancelText="取消"
        confirmLoading={createTaskMutation.isPending || updateTaskMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>

          <Form.Item name="description" label="任务描述">
            <TextArea rows={3} placeholder="请输入任务描述" />
          </Form.Item>

          <Form.Item
            name="trigger_type"
            label="触发方式"
            rules={[{ required: true }]}
          >
            <Select onChange={setTriggerType}>
              <Option value="once">一次性</Option>
              <Option value="interval">间隔执行</Option>
              <Option value="cron">Cron表达式</Option>
            </Select>
          </Form.Item>

          {triggerType === 'once' && (
            <Form.Item
              name="run_at"
              label="执行时间"
              rules={[{ required: true, message: '请选择执行时间' }]}
            >
              <DatePicker showTime style={{ width: '100%' }} />
            </Form.Item>
          )}

          {triggerType === 'interval' && (
            <Form.Item
              name="interval_seconds"
              label="间隔秒数"
              rules={[{ required: true, message: '请输入间隔秒数' }]}
            >
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
          )}

          {triggerType === 'cron' && (
            <Form.Item
              name="cron_expression"
              label="Cron表达式"
              rules={[{ required: true, message: '请输入Cron表达式 (分 时 日 月 周)' }]}
              extra="示例: 0 2 * * * 表示每天凌晨2点执行"
            >
              <Input placeholder="0 2 * * *" />
            </Form.Item>
          )}

          <Form.Item
            name="training_mode"
            label="训练模式"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="full">全量训练</Option>
              <Option value="incremental">增量训练</Option>
            </Select>
          </Form.Item>

          <Form.Item name="school_id" label="学校（可选）">
            <Select placeholder="留空表示全校" allowClear>
              {schools?.map((school) => (
                <Option key={school.id} value={school.id}>
                  {school.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="force_retrain"
            label="强制重新训练"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`执行历史 - ${selectedTask?.name}`}
        open={isHistoryModalVisible}
        onCancel={() => setIsHistoryModalVisible(false)}
        width={800}
        footer={null}
      >
        {executions.length > 0 ? (
          <Timeline
            items={executions.map((execution) => ({
              color: execution.status === 'completed' ? 'green' : execution.status === 'failed' ? 'red' : 'blue',
              dot: getExecutionStatusIcon(execution.status),
              children: (
                <div>
                  <div>
                    <strong>{execution.status === 'completed' ? '执行成功' : execution.status === 'failed' ? '执行失败' : '执行中'}</strong>
                    <span style={{ marginLeft: 8, color: '#999' }}>
                      {new Date(execution.started_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  {execution.completed_at && (
                    <div style={{ color: '#999', fontSize: 12 }}>
                      完成时间: {new Date(execution.completed_at).toLocaleString('zh-CN')}
                    </div>
                  )}
                  {execution.error_message && (
                    <div style={{ color: '#ff4d4f', marginTop: 4 }}>
                      错误: {execution.error_message}
                    </div>
                  )}
                  {execution.training_job_id && (
                    <div style={{ fontSize: 12 }}>
                      训练任务ID: {execution.training_job_id}
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无执行记录
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ScheduledTasks;
