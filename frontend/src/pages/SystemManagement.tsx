import React, { useState } from 'react';
import { Card, Button, Space, Alert, Descriptions, Row, Col, Tag, message, Popconfirm, Timeline } from 'antd';
import { ReloadOutlined, SettingOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const SystemManagement: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // 状态
  const [reloadKey, setReloadKey] = useState(0);
  const [operationHistory, setOperationHistory] = useState<Array<{ time: string; action: string; status: 'success' | 'error' }>>([]);

  // 获取系统配置
  const { data: config, isLoading } = useQuery({
    queryKey: ['system', 'config'],
    queryFn: async () => {
      try {
        const res = await api.get('/system/config');
        return res.data;
      } catch (error) {
        console.error('获取系统配置失败:', error);
        return null;
      }
    },
    enabled: user?.role === 'system_admin',
  });

  // 重载系统配置
  const reloadMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/system/reload');
      return res.data;
    },
    onSuccess: (data: any) => {
      message.success(data.message || '系统配置已重载');
      // 记录操作历史
      setOperationHistory(prev => [
        {
          time: new Date().toLocaleString(),
          action: '重载系统配置',
          status: 'success',
        },
        ...prev,
      ].slice(0, 10)); // 只保留最近10条记录
      // 重新获取配置
      queryClient.invalidateQueries({ queryKey: ['system', 'config'] });
      // 更新reloadKey以触发状态刷新
      setReloadKey(prev => prev + 1);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '重载失败');
      // 记录操作历史
      setOperationHistory(prev => [
        {
          time: new Date().toLocaleString(),
          action: '重载系统配置',
          status: 'error',
        },
        ...prev,
      ].slice(0, 10));
    },
  });

  const handleReload = () => {
    if (window.confirm('确定要重载系统配置吗？\n\n此操作将重新加载.env配置文件和所有Python模块。\n\n注意事项：\n1. 配置修改立即生效\n2. 服务不会重启（仅Python模块重载）\n3. 某些服务可能需要手动重启\n4. 建议在非工作时间操作')) {
      reloadMutation.mutate();
    }
  };

  // 注意：systemConfigData 已被删除，因为直接在JSX中使用多个Descriptions组件

  return (
    <div style={{ padding: '24px' }}>
      <h1>系统管理</h1>

      {/* 系统管理员权限检查 */}
      {user?.role !== 'system_admin' && (
        <Alert
          message="权限不足"
          description="只有系统管理员可以访问系统管理页面"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 操作按钮 */}
      <Card style={{ marginBottom: 16 }}>
        <Space size="large">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReload}
            loading={reloadMutation.isPending}
            danger
          >
            重载系统配置
          </Button>
        </Space>
      </Card>

      {/* 系统配置显示 */}
      {config && (
        <Card
          title={`系统配置 ${reloadKey > 0 ? '(已重载)' : ''}`}
          extra={<Tag color={reloadKey > 0 ? 'green' : 'blue'}>已加载</Tag>}
          loading={isLoading}
        >
          <Descriptions bordered column={1} title="数据库配置">
            <Descriptions.Item label="连接字符串">
              <code>{config.database_url || '未配置'}</code>
            </Descriptions.Item>
            <Descriptions.Item label="推理服务">
              <code>{config.inference_service || '未配置'}</code>
            </Descriptions.Item>
            <Descriptions.Item label="Redis缓存">
              <code>{config.redis || '未配置'}</code>
            </Descriptions.Item>
          </Descriptions>
          <Descriptions bordered column={1} title="文件存储" style={{ marginTop: 16 }}>
            <Descriptions.Item label="上传目录">
              <code>{config.upload_dir || './uploads'}</code>
            </Descriptions.Item>
            <Descriptions.Item label="样本目录">
              <code>{config.samples_dir || './uploads/samples'}</code>
            </Descriptions.Item>
            <Descriptions.Item label="模型目录">
              <code>{config.models_dir || './models'}</code>
            </Descriptions.Item>
            <Descriptions.Item label="最大上传大小">
              <code>{config.max_upload_size || '未配置'} bytes</code>
              <Tag color={config.max_upload_size_mb > 20 ? 'red' : 'green'} style={{ marginLeft: 8 }}>
                {config.max_upload_size_mb || '0'} MB
              </Tag>
            </Descriptions.Item>
          </Descriptions>
          <Descriptions bordered column={1} title="CORS配置" style={{ marginTop: 16 }}>
            <Descriptions.Item label="允许源">
              {Array.isArray(config.cors_origins) ? (
                <Space size={[4, 4]} wrap>
                  {config.cors_origins.map((origin, index) => (
                    <Tag key={index} color="blue">
                      {origin}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Tag color="blue">
                  {config.cors_origins || '未配置'}
                </Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
          <Alert
            message="配置说明"
            description="此页面显示当前系统运行配置。点击'重载系统配置'将重新加载.env文件。"
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Card>
      )}

      {/* 最近操作 */}
      <Card title="最近操作" style={{ marginTop: 16 }}>
        {operationHistory.length > 0 ? (
          <Timeline
            items={operationHistory.map((op, index) => ({
              color: op.status === 'success' ? 'green' : 'red',
              children: (
                <div>
                  <div style={{ fontWeight: 'bold' }}>{op.action}</div>
                  <div style={{ color: '#999', fontSize: '12px' }}>{op.time}</div>
                  <Tag color={op.status === 'success' ? 'success' : 'error'}>
                    {op.status === 'success' ? '成功' : '失败'}
                  </Tag>
                </div>
              ),
            }))}
          />
        ) : (
          <Alert
            message="暂无操作记录"
            description="系统会记录最近的系统管理操作"
            type="info"
            showIcon
          />
        )}
      </Card>
    </div>
  );
};

export default SystemManagement;
