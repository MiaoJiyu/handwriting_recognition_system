import React, { useState } from 'react';
import { Upload, Button, message, Card, Image } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { UploadFile } from 'antd';

const SampleUpload: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [previewImage, setPreviewImage] = useState<string>('');
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/samples/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    },
    onSuccess: () => {
      message.success('上传成功');
      setFileList([]);
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '上传失败');
    },
  });

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请选择文件');
      return;
    }

    const file = fileList[0].originFileObj;
    if (file) {
      uploadMutation.mutate(file);
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
    return false; // 阻止自动上传
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

  return (
    <div>
      <h1>上传样本</h1>
      <Card style={{ marginTop: 24 }}>
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
            onClick={handleUpload}
            loading={uploadMutation.isPending}
            disabled={fileList.length === 0}
          >
            上传
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default SampleUpload;
