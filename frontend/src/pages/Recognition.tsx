import React, { useState } from 'react';
import { Upload, Button, message, Card, Image, Table, Tag, Row, Col } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import type { UploadFile } from 'antd';

const Recognition: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [previewImage, setPreviewImage] = useState<string>('');
  const [result, setResult] = useState<any>(null);

  const recognizeMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/api/recognition', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    },
    onSuccess: (data) => {
      message.success('识别成功');
      setResult(data);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '识别失败');
    },
  });

  const handleRecognize = async () => {
    if (fileList.length === 0) {
      message.warning('请选择文件');
      return;
    }

    const file = fileList[0].originFileObj;
    if (file) {
      recognizeMutation.mutate(file);
    }
  };

  const beforeUpload = (file: File) => {
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('只能上传图片文件');
      return false;
    }
    const isLt10M = file.size / 1024 / 1024 < 10;
    if (!isLt10M) {
      message.error('图片大小不能超过10MB');
      return false;
    }
    return false;
  };

  const handleChange = (info: any) => {
    setFileList(info.fileList);
    if (info.file.originFileObj) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviewImage(e.target?.result as string);
      };
      reader.readAsDataURL(info.file.originFileObj);
    }
  };

  const resultColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (_: any, __: any, index: number) => index + 1,
    },
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '相似度',
      dataIndex: 'score',
      key: 'score',
      render: (score: number) => `${(score * 100).toFixed(2)}%`,
    },
  ];

  return (
    <div>
      <h1>字迹识别</h1>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="上传图片">
            <Upload
              fileList={fileList}
              beforeUpload={beforeUpload}
              onChange={handleChange}
              maxCount={1}
              accept="image/*"
            >
              <Button icon={<UploadOutlined />}>选择图片</Button>
            </Upload>
            {previewImage && (
              <div style={{ marginTop: 16 }}>
                <Image src={previewImage} alt="预览" style={{ maxHeight: 400 }} />
              </div>
            )}
            <div style={{ marginTop: 16 }}>
              <Button
                type="primary"
                onClick={handleRecognize}
                loading={recognizeMutation.isPending}
                disabled={fileList.length === 0}
              >
                开始识别
              </Button>
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="识别结果">
            {result ? (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <Tag color={result.result.is_unknown ? 'red' : 'green'}>
                    {result.result.is_unknown ? '未知用户' : '已识别'}
                  </Tag>
                  <span style={{ marginLeft: 8 }}>
                    置信度: {(result.result.confidence * 100).toFixed(2)}%
                  </span>
                </div>
                {result.result.top_k && result.result.top_k.length > 0 ? (
                  <Table
                    columns={resultColumns}
                    dataSource={result.result.top_k}
                    rowKey="user_id"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <p>未找到匹配结果</p>
                )}
              </div>
            ) : (
              <p>请上传图片并点击"开始识别"</p>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Recognition;
