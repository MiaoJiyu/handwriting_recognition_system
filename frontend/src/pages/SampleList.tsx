import React, { useState, useMemo } from 'react';
import { Table, Button, Image, Popconfirm, message, Space, Card, Row, Col, Tag, Segmented, Tooltip } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { DeleteOutlined, ScissorOutlined, AppstoreOutlined, UnorderedListOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import ImageCropper from '../components/ImageCropper';

// 辅助函数：将后端返回的 image_path 转换为可访问的 URL
const getImageUrl = (imagePath: string | null): string => {
  if (!imagePath) return '';
  // 如果已经是完整 URL，直接返回
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    return imagePath;
  }
  // 从完整路径中提取文件名
  const filename = imagePath.split('/').pop() || '';
  // 构建可访问的 URL
  return `/uploads/${filename}`;
};

interface UserInfo {
  id: number;
  username: string;
  nickname: string | null;
  role: string;
}

interface Sample {
  id: number;
  user_id: number;
  user: UserInfo | null;
  image_path: string;
  image_url: string;
  original_filename: string;
  status: string;
  extracted_region_path: string | null;
  uploaded_at: string;
  sample_regions?: Array<{
    id: number;
    sample_id: number;
    bbox: string;
    is_auto_detected: number;
    created_at: string;
  }>;
}

interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

const SampleList: React.FC = () => {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<string | number>('list');
  const [cropperVisible, setCropperVisible] = useState(false);
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null);

  const { data: samples, isLoading } = useQuery({
    queryKey: ['samples'],
    queryFn: async () => {
      const res = await api.get('/samples');
      return res.data;
    },
  });

  // 获取选中样本的详情（用于加载已保存的裁剪区域）
  const { data: sampleDetail } = useQuery({
    queryKey: ['sample', selectedSample?.id],
    queryFn: async () => {
      if (!selectedSample) return null;
      const res = await api.get(`/samples/${selectedSample.id}`);
      return res.data;
    },
    enabled: !!selectedSample && cropperVisible,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/samples/${id}`);
    },
    onSuccess: () => {
      message.success('删除成功');
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '删除失败');
    },
  });

  const cropMutation = useMutation({
    mutationFn: async ({ sampleId, bbox }: { sampleId: number; bbox: CropArea }) => {
      await api.post(`/samples/${sampleId}/crop`, { bbox });
    },
    onSuccess: () => {
      message.success('裁剪区域已保存，裁剪后的图片已更新');
      queryClient.invalidateQueries({ queryKey: ['samples'] });
      queryClient.invalidateQueries({ queryKey: ['sample', currentSample?.id] });
      setCropperVisible(false);
      setSelectedSample(null);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '裁剪失败');
    },
  });

  const handleCrop = (sample: Sample) => {
    setSelectedSample(sample);
    setCropperVisible(true);
  };

  const handleCropConfirm = (cropArea: CropArea) => {
    if (currentSample) {
      cropMutation.mutate({ sampleId: currentSample.id, bbox: cropArea });
    }
  };

  // 解析已保存的裁剪区域（使用样本详情中的sample_regions）
  const getSavedCropArea = (): CropArea | null => {
    if (sampleDetail?.sample_regions && sampleDetail.sample_regions.length > 0) {
      try {
        // 优先查找手动标注的区域（is_auto_detected === 0）
        const manualRegion = sampleDetail.sample_regions.find(
          region => region.is_auto_detected === 0
        );
        if (manualRegion) {
          const bbox = JSON.parse(manualRegion.bbox);
          return bbox as CropArea;
        }

        // 如果没有手动标注，使用第一个自动检测的区域
        const autoRegion = sampleDetail.sample_regions[0];
        if (autoRegion) {
          const bbox = JSON.parse(autoRegion.bbox);
          return bbox as CropArea;
        }
      } catch (e) {
        console.error('Failed to parse saved crop area:', e);
      }
    }
    return null;
  };

  // 使用样本详情数据作为selectedSample（如果已加载）
  const currentSample = sampleDetail || selectedSample;

  const getStatusTag = (status: string) => {
    const statusMap: { [key: string]: { color: string; text: string } } = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      processed: { color: 'success', text: '已处理' },
      failed: { color: 'error', text: '处理失败' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '学生',
      dataIndex: 'user',
      key: 'user',
      width: 150,
      render: (user: UserInfo | null) => {
        if (!user) return '-';
        return user.nickname ? `${user.nickname} (${user.username})` : user.username;
      },
    },
    {
      title: '预览',
      dataIndex: 'image_path',
      key: 'preview',
      width: 150,
      render: (_path: string, record: Sample) => {
        const url = record.image_url || getImageUrl(record.image_path);
        return (
          <Image
            src={url}
            width={100}
            height={100}
            style={{ objectFit: 'cover' }}
            alt="预览"
            fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect width='100%25' height='100%25' fill='%23f5f5f5'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999' font-size='12'%3EImage%20Error%3C/text%3E%3C/svg%3E"
            onError={() => {
              message.warning(`图片加载失败: ${url}`);
            }}
          />
        );
      },
    },
    {
      title: '文件名',
      dataIndex: 'original_filename',
      key: 'original_filename',
      render: (filename: string, record: Sample) => (
        <a onClick={() => {
          const url = record.image_url || getImageUrl(record.image_path);
          const img = new Image();
          img.src = url;
          img.onload = () => {
            const width = Math.min(img.width, 800);
            const height = Math.min(img.height, 600);
            const win = window.open('', '_blank');
            if (win) {
              win.document.write(`
                <html>
                  <head><title>${filename}</title></head>
                  <body style="margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#f0f0f0;">
                    <img src="${url}" style="max-width:100%;max-height:100%;object-fit:contain;" />
                  </body>
                </html>
              `);
              win.document.close();
            }
          };
        }}>
          {filename}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
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
      width: 180,
      render: (_: any, record: Sample) => (
        <Space>
          <Button
            icon={<ScissorOutlined />}
            size="small"
            onClick={() => handleCrop(record)}
          >
            裁剪
          </Button>
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
        </Space>
      ),
    },
  ];

  // 画廊视图
  const renderGalleryView = () => (
    <Row gutter={[16, 16]}>
      {samples?.map((sample: Sample) => {
        // 优先显示裁剪后的图片，否则显示原图
        const displayImageUrl = sample.extracted_region_path
          ? getImageUrl(sample.extracted_region_path)
          : (sample.image_url || getImageUrl(sample.image_path));

        return (
          <Col key={sample.id} xs={24} sm={12} md={8} lg={6} xl={4}>
            <Card
              hoverable
              cover={
                <div style={{ height: 200, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
                  <Image
                    src={displayImageUrl}
                    alt={sample.original_filename}
                    style={{ maxWidth: '100%', maxHeight: 200, objectFit: 'contain' }}
                    preview={{ mask: '查看大图' }}
                  />
                </div>
              }
              extra={
                sample.extracted_region_path ? (
                  <Tag color="success" style={{ fontSize: 10, marginTop: 8 }}>已裁剪</Tag>
                ) : null
              }
              actions={[
                <ScissorOutlined key="crop" onClick={() => handleCrop(sample)} title="裁剪" />,
                <Popconfirm
                  key="delete"
                  title="确定要删除这个样本吗？"
                  onConfirm={() => deleteMutation.mutate(sample.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <DeleteOutlined style={{ color: '#ff4d4f' }} title="删除" />
                </Popconfirm>,
              ]}
            >
              <Card.Meta
                title={
                  <span style={{ fontSize: 12, wordBreak: 'break-all' }}>
                    {sample.original_filename.length > 20
                      ? sample.original_filename.substring(0, 20) + '...'
                      : sample.original_filename}
                  </span>
                }
                description={
                  <div style={{ fontSize: 12 }}>
                    <div style={{ marginBottom: 4, color: '#666' }}>
                      {sample.user
                        ? sample.user.nickname
                          ? `${sample.user.nickname} (${sample.user.username})`
                          : sample.user.username
                        : '-'}
                    </div>
                    {getStatusTag(sample.status)}
                    <div style={{ marginTop: 4, color: '#999' }}>
                      {new Date(sample.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>
                }
              />
            </Card>
          </Col>
        );
      })}
    </Row>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>样本管理</h1>
        <Segmented
          options={[
            { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
            { value: 'gallery', icon: <AppstoreOutlined />, label: '画廊' },
          ]}
          value={viewMode}
          onChange={setViewMode}
        />
      </div>
      
      {viewMode === 'list' ? (
        <Table
          columns={columns}
          dataSource={samples}
          loading={isLoading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      ) : (
        renderGalleryView()
      )}

      {currentSample && (
        <ImageCropper
          visible={cropperVisible}
          imageUrl={currentSample.image_url || getImageUrl(currentSample.image_path)}
          onCrop={handleCropConfirm}
          onCancel={() => {
            setCropperVisible(false);
            setSelectedSample(null);
          }}
          title={`裁剪图片 - ${currentSample.original_filename}`}
          initialCropArea={getSavedCropArea()}
        />
      )}
    </div>
  );
};

export default SampleList;
