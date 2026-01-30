import React, { useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, Space, Tabs, Upload, Card, Tag, Alert, Row, Col, Popconfirm } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { PlusOutlined, DownloadOutlined, UploadOutlined, FileExcelOutlined, ExportOutlined, PlusCircleOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import * as XLSX from 'xlsx';

const { TabPane } = Tabs;

interface Student {
  id: number;
  username: string;
  nickname: string | null;
  role: string;
  school_id: number | null;
  created_at: string;
}

interface School {
  id: number;
  name: string;
}

interface BatchStudentData {
  username: string;
  nickname: string;
  password?: string;
}

const UserManagement: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // 状态
  const [modalVisible, setModalVisible] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'batch' | 'import' | 'edit'>('create');
  const [selectedSchool, setSelectedSchool] = useState<number | undefined>();
  const [activeTab, setActiveTab] = useState('students');
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [fileList, setFileList] = useState<any[]>([]);
  const [selectedUser, setSelectedUser] = useState<Student | null>(null);

  // 获取用户列表
  const { data: users, isLoading } = useQuery<Student[]>({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await api.get('/users');
      return res.data;
    },
  });

  // 获取学校列表
  const { data: schools } = useQuery<School[]>({
    queryKey: ['schools'],
    queryFn: async () => {
      const res = await api.get('/schools');
      return res.data;
    },
    enabled: user?.role === 'system_admin',
  });

  // 过滤用户（根据选中的学校）
  const filteredUsers = React.useMemo(() => {
    if (!users) return [];
    if (user?.role === 'school_admin' && selectedSchool) {
      return users.filter(u => u.school_id === selectedSchool);
    }
    if (user?.role === 'system_admin' && selectedSchool) {
      return users.filter(u => u.school_id === selectedSchool);
    }
    return users;
  }, [users, selectedSchool, user]);

  // 创建单个用户
  const createMutation = useMutation({
    mutationFn: async (values: any) => {
      const res = await api.post('/users', values);
      return res.data;
    },
    onSuccess: () => {
      message.success('创建成功');
      setModalVisible(false);
      setSelectedUser(null);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('创建失败');
    },
  });

  // 更新用户
  const updateMutation = useMutation({
    mutationFn: async ({ userId, values }: { userId: number; values: any }) => {
      const res = await api.put(`/users/${userId}`, values);
      return res.data;
    },
    onSuccess: () => {
      message.success('更新成功');
      setModalVisible(false);
      setSelectedUser(null);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  // 删除用户
  const deleteMutation = useMutation({
    mutationFn: async (userId: number) => {
      await api.delete(`/users/${userId}`);
    },
    onSuccess: () => {
      message.success('删除成功');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '删除失败');
    },
  });

  // 批量创建学生
  const batchCreateMutation = useMutation({
    mutationFn: async (values: any) => {
      const res = await api.post('/users/batch', values);
      return res.data;
    },
    onSuccess: (data: any) => {
      message.success(`批量创建完成！成功：${data.success}，失败：${data.failed}`);
      setModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      batchForm.resetFields();
    },
    onError: (error: any) => {
      message.error(`批量创建失败：${error.response?.data?.detail || error.message}`);
    },
  });

  // 导出学生名单
  const exportMutation = useMutation({
    mutationFn: async () => {
      const schoolId = selectedSchool || (user?.role === 'school_admin' ? user.school_id : undefined);
      const url = schoolId ? `/users/export?school_id=${schoolId}` : '/users/export';
      const res = await api.get(url, { responseType: 'blob' });
      return res.data;
    },
    onSuccess: (data: Blob) => {
      // 下载文件
      const url = window.URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `students_${new Date().getTime()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success('导出成功');
    },
    onError: () => {
      message.error('导出失败');
    },
  });

  // 下载模板
  const downloadTemplate = async () => {
    try {
      const res = await api.get('/users/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'student_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success('模板下载成功');
    } catch (error) {
      message.error('模板下载失败');
    }
  };

  // 处理编辑用户
  const handleEditUser = (user: Student) => {
    setSelectedUser(user);
    setModalType('edit');
    setModalVisible(true);
    form.setFieldsValue({
      username: user.username,
      nickname: user.nickname,
      role: user.role,
      school_id: user.school_id,
    });
  };

  // 处理创建用户（清空表单）
  const handleCreateUser = () => {
    setSelectedUser(null);
    setModalType('create');
    setModalVisible(true);
    form.resetFields();
  };

  // 处理提交（创建或更新）
  const handleSubmit = (values: any) => {
    if (selectedUser) {
      updateMutation.mutate({ userId: selectedUser.id, values });
    } else {
      createMutation.mutate(values);
    }
  };

  // 手动添加学生（在批量创建表单中）
  const handleAddStudent = () => {
    const students = batchForm.getFieldValue('students') || [];
    batchForm.setFieldValue('students', [
      ...students,
      { username: '', nickname: '', password: '' },
    ]);
  };

  // 处理Excel导入
  const handleImport = async (file: File) => {
    try {
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });

      const students = jsonData.map((row: any) => ({
        username: row['学号'] || row['username'],
        nickname: row['姓名'] || row['nickname'] || row['姓名(昵称)'],
        password: row['密码'] || row['password'],
      }));

      batchCreateMutation.mutate({
        students,
        auto_generate_username: false,
        auto_generate_password: false,
      });
    } catch (error) {
      message.error('文件解析失败，请检查格式');
    }
  };

  // 批量创建提交
  const handleBatchSubmit = () => {
    const values = batchForm.getFieldsValue();
    values.students = values.students.filter((s: BatchStudentData) => s.username);

    batchCreateMutation.mutate({
      students: values.students,
      auto_generate_username: values.auto_generate_username || false,
      auto_generate_password: values.auto_generate_password || false,
    });
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '学号',
      dataIndex: 'username',
      key: 'username',
      width: 120,
    },
    {
      title: '姓名',
      dataIndex: 'nickname',
      key: 'nickname',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role: string) => {
        const roleMap: Record<string, { text: string; color: string }> = {
          student: { text: '学生', color: 'green' },
          teacher: { text: '教师', color: 'blue' },
          school_admin: { text: '学校管理员', color: 'orange' },
          system_admin: { text: '系统管理员', color: 'red' },
        };
        const config = roleMap[role] || { text: role, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '学校',
      dataIndex: 'school_id',
      key: 'school_id',
      width: 150,
      render: (schoolId: number) => {
        if (!schools) return schoolId;
        const school = schools.find((s: School) => s.id === schoolId);
        return school ? school.name : `学校 ${schoolId}`;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => {
        if (!date) return '-';
        try {
          const d = new Date(date);
          if (isNaN(d.getTime())) return date; // 如果无效，返回原字符串
          return d.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          });
        } catch {
          return date;
        }
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: Student) => {
        const canEdit = user?.role === 'system_admin' ||
                         (user?.role === 'school_admin' && user.school_id === record.school_id);
        const canDelete = user?.role === 'system_admin';
        return (
          <Space size="small">
            {canEdit && (
              <Button
                type="link"
                size="small"
                onClick={() => handleEditUser(record)}
              >
                编辑
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="确定要删除这个用户吗？"
                onConfirm={() => deleteMutation.mutate(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" danger size="small">
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <h1>用户管理</h1>

      {/* 学校管理员和系统管理员可以筛选学校 */}
      {(user?.role === 'school_admin' || user?.role === 'system_admin') && schools && (
        <Card style={{ marginBottom: 16 }}>
          <Space>
            <span>学校筛选：</span>
            <Select
              style={{ width: 200 }}
              placeholder="选择学校"
              allowClear
              onChange={(value) => setSelectedSchool(value)}
              value={selectedSchool}
            >
              {schools.map((school: School) => (
                <Select.Option key={school.id} value={school.id}>
                  {school.name}
                </Select.Option>
              ))}
            </Select>
          </Space>
        </Card>
      )}

      {/* 操作按钮 */}
      <Card style={{ marginBottom: 16 }}>
        <Space size="large">
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateUser}>
            创建用户
          </Button>
          <Button icon={<PlusCircleOutlined />} onClick={() => {
            setSelectedUser(null);
            setModalType('batch');
            setModalVisible(true);
          }}>
            批量创建学生
          </Button>
          <Button icon={<UploadOutlined />} onClick={() => {
            setSelectedUser(null);
            setModalType('import');
            setModalVisible(true);
          }}>
            导入学生名单
          </Button>
          <Button icon={<FileExcelOutlined />} onClick={downloadTemplate}>
            下载模板
          </Button>
          <Button icon={<ExportOutlined />} onClick={() => exportMutation.mutate()} loading={exportMutation.isPending}>
            导出学生名单
          </Button>
        </Space>
      </Card>

      {/* 用户列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredUsers}
          loading={isLoading}
          rowKey="id"
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 人`,
          }}
        />
      </Card>

      {/* 创建/批量创建/导入/编辑 模态框 */}
      <Modal
        title={modalType === 'batch' ? '批量创建学生' : modalType === 'import' ? '导入学生名单' : modalType === 'edit' ? '编辑用户' : '创建用户'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setSelectedUser(null);
          form.resetFields();
          batchForm.resetFields();
          setFileList([]);
        }}
        width={modalType === 'batch' || modalType === 'import' ? 800 : 500}
        footer={[
          <Button key="cancel" onClick={() => {
            setModalVisible(false);
            setSelectedUser(null);
            form.resetFields();
            batchForm.resetFields();
            setFileList([]);
          }}>
            取消
          </Button>,
          modalType === 'import' ? (
            <Button
              key="submit"
              type="primary"
              onClick={() => {
                if (fileList.length > 0) {
                  handleImport(fileList[0].originFileObj);
                }
              }}
              disabled={fileList.length === 0}
            >
              导入
            </Button>
          ) : (
            <Button
              key="submit"
              type="primary"
              onClick={() => modalType === 'batch' ? handleBatchSubmit() : form.submit()}
              loading={createMutation.isPending || updateMutation.isPending || batchCreateMutation.isPending}
            >
              {modalType === 'edit' ? '更新' : '确定'}
            </Button>
          ),
        ]}
      >
        <Tabs activeKey={modalType === 'edit' ? 'create' : modalType} onChange={(key) => {
          if (key !== 'edit') {
            setModalType(key as any);
          }
        }}>
          <TabPane tabKey="create" key="create">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
            >
              <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                <Input disabled={modalType === 'edit'} />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={modalType === 'edit' ? [] : [{ required: true }]}>
                <Input.Password placeholder={modalType === 'edit' ? '留空则不修改密码' : ''} />
              </Form.Item>
              <Form.Item name="nickname" label="昵称（学生姓名）">
                <Input />
              </Form.Item>
              <Form.Item name="role" label="角色" rules={[{ required: true }]}>
                <Select disabled={modalType === 'edit'}>
                  <Select.Option value="student">学生</Select.Option>
                  <Select.Option value="teacher">教师</Select.Option>
                  {user?.role === 'system_admin' && (
                    <Select.Option value="school_admin">学校管理员</Select.Option>
                  )}
                </Select>
              </Form.Item>
              {user?.role === 'system_admin' && schools && (
                <Form.Item name="school_id" label="学校">
                  <Select placeholder="选择学校">
                    {schools.map((school: School) => (
                      <Select.Option key={school.id} value={school.id}>
                        {school.name}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              )}
            </Form>
          </TabPane>

          <TabPane tabKey="batch" key="batch">
            <Form form={batchForm} layout="vertical" initialValues={{ students: [{ username: '', nickname: '', password: '' }], auto_generate_username: false, auto_generate_password: false }}>
              <Alert
                message="批量创建说明"
                description="可以手动输入学生信息，也可以自动生成学号和密码。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Form.Item name="auto_generate_username" valuePropName="checked">
                <span>自动生成学号（格式：2024XXXX）</span>
              </Form.Item>
              <Form.Item name="auto_generate_password" valuePropName="checked">
                <span>自动生成密码（8位，包含字母和数字）</span>
              </Form.Item>
              <Form.List name="students">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map((field, index) => (
                      <Space key={field.key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                        <Form.Item
                          name={[field.name, 'username']}
                          rules={[{ required: true }]}
                          style={{ marginBottom: 0, width: 150 }}
                        >
                          <Input placeholder="学号（或留空自动生成）" />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'nickname']}
                          style={{ marginBottom: 0, width: 150 }}
                        >
                          <Input placeholder="姓名" />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'password']}
                          style={{ marginBottom: 0, width: 150 }}
                        >
                          <Input.Password placeholder="密码（或留空自动生成）" />
                        </Form.Item>
                        <Button type="link" danger onClick={() => remove(field.name)}>
                          删除
                        </Button>
                      </Space>
                    ))}
                    <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />}>
                      添加学生
                    </Button>
                  </>
                )}
              </Form.List>
            </Form>
          </TabPane>

          <TabPane tabKey="import" key="import">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Alert
                message="导入说明"
                description="请上传Excel文件，文件应包含以下列：学号、姓名（昵称）、密码。如果不包含密码，将使用自动生成的密码。"
                type="info"
                showIcon
              />
              <Upload.Dragger
                accept=".xlsx,.xls"
                maxCount={1}
                fileList={fileList}
                beforeUpload={(file) => {
                  const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                                file.type === 'application/vnd.ms-excel';
                  if (!isExcel) {
                    message.error('只能上传Excel文件');
                    return Upload.LIST_IGNORE;
                  }
                  return false;
                }}
                onChange={({ fileList }) => setFileList(fileList)}
              >
                <p className="ant-upload-drag-icon">
                  <UploadOutlined />
                  <p>点击或拖拽Excel文件到此处上传</p>
                </p>
              </Upload.Dragger>
            </Space>
          </TabPane>
        </Tabs>
      </Modal>
    </div>
  );
};

export default UserManagement;
