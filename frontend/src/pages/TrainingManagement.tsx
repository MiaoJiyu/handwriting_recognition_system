import React, { useState } from 'react';
import { Table, Button, message, Card } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { PlayCircleOutlined } from '@ant-design/icons';

const TrainingManagement: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['training-jobs'],
    queryFn: async () => {
      const res = await api.get('/training');
      return res.data;
    },
  });

  const startTrainingMutation = useMutation({
    mutationFn: async () => {
      await api.post('/training', { force_retrain: false });
    },
    onSuccess: () => {
      message.success('训练任务已启动');
      queryClient.invalidateQueries({ queryKey: ['training-jobs'] });
    },
    onError: () => {
      message.error('启动训练失败');
    },
  });

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
      render: (text: string) => new Date(text).toLocaleString(),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>训练管理</h1>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={() => startTrainingMutation.mutate()}
          loading={startTrainingMutation.isPending}
        >
          启动训练
        </Button>
      </div>
      <Card title="训练任务" style={{ marginBottom: 24 }}>
        <Table columns={columns} dataSource={jobs} loading={isLoading} rowKey="id" />
      </Card>
    </div>
  );
};

export default TrainingManagement;
