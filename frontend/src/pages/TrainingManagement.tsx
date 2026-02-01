import React, { useState } from 'react';
import { Table, Button, message, Card, Tag, Tooltip, Space, Modal } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { PlayCircleOutlined, ReloadOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { formatDateToLocal } from '../utils/datetime';

const TrainingManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const [trainingType, setTrainingType] = useState<'full' | 'incremental' | null>(null);

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['training-jobs'],
    queryFn: async () => {
      const res = await api.get('/training');
      return res.data;
    },
  });

  const startTrainingMutation = useMutation({
    mutationFn: async (forceRetrain: boolean) => {
      await api.post('/training', { force_retrain: forceRetrain });
    },
    onSuccess: (_, forceRetrain) => {
      const trainingTypeName = forceRetrain ? '全量训练' : '增量训练';
      message.success(`${trainingTypeName}任务已启动`);
      setTrainingType(null);
      queryClient.invalidateQueries({ queryKey: ['training-jobs'] });
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      message.error(detail ? `启动训练失败：${detail}` : '启动训练失败');
      setTrainingType(null);
    },
  });

  const handleStartTraining = (forceRetrain: boolean, type: 'full' | 'incremental') => {
    Modal.confirm({
      title: '确认启动训练',
      icon: <ExclamationCircleOutlined />,
      content: `确定要启动${forceRetrain ? '全量训练' : '增量训练'}吗？${forceRetrain ? '全量训练会重新训练整个模型，耗时较长。' : '增量训练会在现有模型基础上进行微调，速度较快。'}`,
      okText: '确定',
      cancelText: '取消',
      onOk: () => {
        setTrainingType(type);
        startTrainingMutation.mutate(forceRetrain);
      },
    });
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'geekblue';
        if (status === 'completed') {
          color = 'green';
        } else if (status === 'failed') {
          color = 'volcano';
        } else if (status === 'running') {
          color = 'processing';
        }
        return <Tag color={color}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => (progress * 100).toFixed(2) + '%',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => formatDateToLocal(text) || '-',
    },
    {
      title: '详情',
      dataIndex: 'error_message',
      key: 'error_message',
      render: (text: string) => text ? <Tooltip title={text}>{text.substring(0, 50)}...</Tooltip> : '-',
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>训练管理</h1>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => handleStartTraining(true, 'full')}
            loading={startTrainingMutation.isPending && trainingType === 'full'}
          >
            全量训练
          </Button>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleStartTraining(false, 'incremental')}
            loading={startTrainingMutation.isPending && trainingType === 'incremental'}
          >
            增量训练
          </Button>
        </Space>
      </div>
      <Card title="训练任务" style={{ marginBottom: 24 }}>
        <Table columns={columns} dataSource={jobs} loading={isLoading} rowKey="id" />
      </Card>
    </div>
  );
};

export default TrainingManagement;
