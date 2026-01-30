import React, { useState } from 'react';
import { Upload, Button, message, Card, Image, Form, Select } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { configService } from '../services/config';
import type { UploadFile } from 'antd';
import { useAuth } from '../contexts/AuthContext';

const { Option } = Select;

const SampleUpload: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [previewImage, setPreviewImage] = useState<string>('');
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // 获取系统配置
  const { data: config } = useQuery({
    queryKey: ['config'],
    queryFn: configService.getConfig,
    staleTime: 5 * 60 * 1000, // 5分钟内不重新请求
  });

  const maxUploadSizeMB = config?.max_upload_size_mb || 10;

  // 获取用户列表（只获取学生）
  const { data: students, isLoading: isLoadingStudents } = useQuery({
    queryKey: ['students'],
    queryFn: async () => {
      const res = await api.get('/users?role=student');
      return res.data;
    },
    enabled: !!user && (user.role === 'teacher' || user.role === 'school_admin' || user.role === 'system_admin'),
  });

  const uploadMutation = useMutation({
    mutationFn: async (values: any) => {
      const { studentId, file } = values;
      const formData = new FormData();
      formData.append('file', file);
      if (studentId) {
        formData.append('student_id', studentId);
      }
      
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
      setPreviewImage('');
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '上传失败');
    },
  });

  const beforeUpload = (file: File) => {
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('只能上传图片文件');
      return false;
    }
    const isLtMax = file.size / 1024 / 1024 < maxUploadSizeMB;
    if (!isLtMax) {
      message.error(`图片大小不能超过${maxUploadSizeMB}MB`);
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

  const handleSubmit = () => {
    if (fileList.length === 0) {
      message.warning('请选择文件');
      return;
    }

    const file = fileList[0].originFileObj;
    if (!file) {
      message.warning('文件无效');
      return;
    }

    const formValues = form.getFieldsValue();
    uploadMutation.mutate({
      studentId: formValues.studentId,
      file: file,
    });
  };

  // 检查是否是教师及以上权限
  const isTeacherOrAbove = user && (user.role === 'teacher' || user.role === 'school_admin' || user.role === 'system_admin');

  return (
    <div>
      <h1>上传样本</h1>
      <Card style={{ marginTop: 24 }}>
        <Form form={form} layout="vertical">
          {/* 学生选择框（仅教师及以上权限可见） */}
          {isTeacherOrAbove && (
            <Form.Item 
              name="studentId" 
              label="选择学生"
              rules={[{ required: false }]}
              help="如果不选择，样本将属于您自己"
            >
              <Select
                placeholder="选择学生（可选）"
                loading={isLoadingStudents}
                allowClear
              >
                {students?.map((student: any) => (
                  <Option key={student.id} value={student.id.toString()}>
                    {student.nickname ? `${student.nickname} (${student.username})` : student.username}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          )}

          {/* 文件上传组件 */}
          <Form.Item
            name="file"
            label="选择图片文件"
            rules={[{ required: true, message: '请选择图片文件' }]}
          >
            <Upload
              fileList={fileList}
              beforeUpload={beforeUpload}
              onChange={handleChange}
              maxCount={1}
              accept="image/*"
            >
              <Button icon={<UploadOutlined />}>选择图片</Button>
            </Upload>
          </Form.Item>

          {/* 图片预览 */}
          {previewImage && (
            <div style={{ marginTop: 16 }}>
              <Image src={previewImage} alt="预览" style={{ maxHeight: 400 }} />
            </div>
          )}

          {/* 提交按钮 */}
          <div style={{ marginTop: 16 }}>
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={uploadMutation.isPending}
              disabled={fileList.length === 0}
            >
              上传
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default SampleUpload;
