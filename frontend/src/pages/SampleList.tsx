import React from 'react';
import { Table, Button, Image, Popconfirm, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { DeleteOutlined } from '@ant-design/icons';

const SampleList: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: samples, isLoading } = useQuery({
    queryKey: ['samples'],
    queryFn: async () => {
      const res = await api.get('/api/samples');
      return res.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/samples/${id}`);
    },
    onSuccess: () => {
      message.success('删除成功');
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '删除失败');
    },
  });

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '预览',
      dataIndex: 'image_path',
      key: 'preview',
      width: 150,
      render: (path: string) => (
        <Image src={path} width={100} height={100} style={{ objectFit: 'cover' }} alt="预览" />
      ),
    },
    {
      title: '文件名',
      dataIndex: 'original_filename',
      key: 'original_filename',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
    },
    {
      title: '上传时间',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <Popconfirm
          title="确定要删除这个样本吗？"
          onConfirm={() => deleteMutation.mutate(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <h1>样本管理</h1>
      <Table
        columns={columns}
        dataSource={samples}
        loading={isLoading}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default SampleList;
