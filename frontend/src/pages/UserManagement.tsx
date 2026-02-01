import React, { useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, Space, Tabs, Upload, Card, Tag, Alert, Popconfirm, Divider } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { PlusOutlined, UploadOutlined, FileExcelOutlined, ExportOutlined, PlusCircleOutlined, DeleteOutlined, LockOutlined, SwapOutlined, LogoutOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import * as XLSX from 'xlsx';
import { formatDateToLocalZh } from '../utils/datetime';

const { TabPane } = Tabs;

interface Student {
  id: number;
  username: string;
  nickname: string | null;
  role: string;
  school_id: number | null;
  created_at: string;
  switched_user_id?: number | null;
}

interface School {
  id: number;
  name: string;
  created_at: string;
  user_count?: number;
}

interface BatchStudentData {
  username: string;
  nickname: string;
  password?: string;
  school_id?: number;
}

const UserManagement: React.FC = () => {
  const { user, fetchUser } = useAuth();
  const queryClient = useQueryClient();

  // 状态
  const [activeTab, setActiveTab] = useState<'users' | 'schools'>('users');
  const [modalVisible, setModalVisible] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'batch' | 'import' | 'edit' | 'password' | 'school_create' | 'school_edit'>('create');
  const [selectedSchool, setSelectedSchool] = useState<number | undefined>();
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [fileList, setFileList] = useState<any[]>([]);
  const [selectedUser, setSelectedUser] = useState<Student | null>(null);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [exportFilters, setExportFilters] = useState<{
    school_id?: number;
    role?: string;
  }>({});
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [switchModalVisible, setSwitchModalVisible] = useState(false);
  const [switchTargetUser, setSwitchTargetUser] = useState<Student | null>(null);
  const [batchSchoolModalVisible, setBatchSchoolModalVisible] = useState(false);
  const [batchPasswordModalVisible, setBatchPasswordModalVisible] = useState(false);
  const [batchSchoolForm] = Form.useForm();
  const [batchPasswordForm] = Form.useForm();

  // 学校管理相关状态
  const [selectedSchoolForManage, setSelectedSchoolForManage] = useState<School | null>(null);
  const [schoolModalVisible, setSchoolModalVisible] = useState(false);
  const [schoolModalType, setSchoolModalType] = useState<'create' | 'edit'>('create');
  const [schoolForm] = Form.useForm();

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

  // 学校管理 - 获取学校列表（带用户数量）
  const { data: schoolsWithUsers, isLoading: schoolsLoading } = useQuery<School[]>({
    queryKey: ['schools_with_users'],
    queryFn: async () => {
      const res = await api.get('/schools');
      return res.data;
    },
    enabled: activeTab === 'schools' && user?.role === 'system_admin',
  });

  // 学校管理 - 创建学校
  const createSchoolMutation = useMutation({
    mutationFn: async (values: { name: string }) => {
      const res = await api.post('/schools', values);
      return res.data;
    },
    onSuccess: () => {
      message.success('学校创建成功');
      setSchoolModalVisible(false);
      schoolForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['schools'] });
      queryClient.invalidateQueries({ queryKey: ['schools_with_users'] });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '学校创建失败');
    },
  });

  // 学校管理 - 更新学校
  const updateSchoolMutation = useMutation({
    mutationFn: async ({ schoolId, values }: { schoolId: number; values: { name: string } }) => {
      const res = await api.put(`/schools/${schoolId}`, values);
      return res.data;
    },
    onSuccess: () => {
      message.success('学校更新成功');
      setSchoolModalVisible(false);
      setSelectedSchoolForManage(null);
      schoolForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['schools'] });
      queryClient.invalidateQueries({ queryKey: ['schools_with_users'] });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '学校更新失败');
    },
  });

  // 学校管理 - 删除学校
  const deleteSchoolMutation = useMutation({
    mutationFn: async (schoolId: number) => {
      await api.delete(`/schools/${schoolId}`);
    },
    onSuccess: () => {
      message.success('学校删除成功');
      queryClient.invalidateQueries({ queryKey: ['schools'] });
      queryClient.invalidateQueries({ queryKey: ['schools_with_users'] });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '学校删除失败');
    },
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
      setSelectedRowKeys([]);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '删除失败');
    },
  });

  // 批量删除用户
  const batchDeleteMutation = useMutation({
    mutationFn: async (userIds: number[]) => {
      const res = await api.delete('/users/batch', { data: { user_ids: userIds } });
      return res.data;
    },
    onSuccess: (data) => {
      if (data.failed > 0) {
        message.warning(`批量删除完成：成功 ${data.success} 个，失败 ${data.failed} 个`);
      } else {
        message.success(`成功删除 ${data.success} 个用户`);
      }
      setSelectedRowKeys([]);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '批量删除失败');
    },
  });

  // 批量设置学校
  const batchSetSchoolMutation = useMutation({
    mutationFn: async ({ user_ids, school_id }: { user_ids: number[]; school_id: number }) => {
      const res = await api.put('/users/batch/school', { user_ids, school_id });
      return res.data;
    },
    onSuccess: (data) => {
      if (data.failed > 0) {
        message.warning(`批量设置学校完成：成功 ${data.success} 个，失败 ${data.failed} 个`);
      } else {
        message.success(`成功为 ${data.success} 个用户设置学校`);
      }
      setBatchSchoolModalVisible(false);
      batchSchoolForm.resetFields();
      setSelectedRowKeys([]);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '批量设置学校失败');
    },
  });

  // 批量重置密码
  const batchResetPasswordMutation = useMutation({
    mutationFn: async ({ user_ids, password }: { user_ids: number[]; password?: string }) => {
      const params = new URLSearchParams();
      if (password) {
        params.append('password', password);
      }
      const url = `/users/batch/reset-password${params.toString() ? '?' + params.toString() : ''}`;

      const res = await api.put(url, { user_ids }, { responseType: 'blob' });
      return res.data;
    },
    onSuccess: (data: Blob) => {
      // 下载Excel文件
      const url = window.URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `password_reset_results_${new Date().getTime()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      message.success('密码重置成功，结果已下载');
      setBatchPasswordModalVisible(false);
      batchPasswordForm.resetFields();
      setSelectedRowKeys([]);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '批量重置密码失败');
    },
  });

  // 修改密码
  const changePasswordMutation = useMutation({
    mutationFn: async ({ userId, password }: { userId: number; password: string }) => {
      await api.put(`/users/${userId}`, { password });
    },
    onSuccess: () => {
      message.success('密码修改成功');
      setModalVisible(false);
      setSelectedUser(null);
      form.resetFields();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '密码修改失败');
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
      setSelectedUser(null);
      batchForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(`批量创建失败：${error.response?.data?.detail || error.message}`);
    },
  });

  // 导出学生名单
  const exportMutation = useMutation({
    mutationFn: async (filters: { school_id?: number; role?: string }) => {
      const params = new URLSearchParams();
      if (filters.school_id) params.append('school_id', filters.school_id.toString());
      if (filters.role) params.append('role', filters.role);
      const url = `/users/export${params.toString() ? '?' + params.toString() : ''}`;
      const res = await api.get(url, { responseType: 'blob' });
      return res.data;
    },
    onSuccess: (data: Blob) => {
      const url = window.URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `students_${new Date().getTime()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success('导出成功');
      setExportModalVisible(false);
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
  const handleEditUser = (record: Student) => {
    setSelectedUser(record);
    setModalType('edit');
    setModalVisible(true);
    form.setFieldsValue({
      username: record.username,
      nickname: record.nickname,
      role: record.role,
      school_id: record.school_id,
    });
  };

  // 处理修改密码
  const handleChangePassword = (record: Student) => {
    setSelectedUser(record);
    setModalType('password');
    setModalVisible(true);
    form.resetFields();
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

  // 处理批量创建提交
  const handleBatchSubmit = () => {
    const values = batchForm.getFieldsValue();
    batchCreateMutation.mutate(values);
  };

  // 手动添加学生（在批量创建表单中）

  // 处理Excel导入
  const handleImport = async (file: File) => {
    try {
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });

      const defaultSchoolId = batchForm.getFieldValue('batch_school_id') || user?.school_id;

      const students = jsonData.map((row: any) => ({
        username: row['学号'] || row['username'],
        nickname: row['姓名'] || row['nickname'] || row['姓名(昵称)'],
        password: row['密码'] || row['password'],
        school_id: row['学校'] || defaultSchoolId,
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

  // 处理导出
  const handleExport = () => {
    setExportModalVisible(true);
    if (user?.role === 'school_admin' && user.school_id) {
      setExportFilters({
        school_id: user.school_id,
        role: 'student'
      });
    } else if (user?.role === 'teacher' && user.school_id) {
      setExportFilters({
        school_id: user.school_id,
        role: 'student'
      });
    } else {
      setExportFilters({ role: 'student' });
    }
  };

  // 提交导出筛选
  const handleExportSubmit = () => {
    exportMutation.mutate(exportFilters);
  };

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请至少选择一个用户');
      return;
    }
    Modal.confirm({
      title: `确定要删除选中的 ${selectedRowKeys.length} 个用户吗？`,
      content: '删除后无法恢复，请谨慎操作',
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        batchDeleteMutation.mutate(selectedRowKeys as number[]);
      },
    });
  };

  // 批量设置学校
  const handleBatchSetSchool = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请至少选择一个用户');
      return;
    }
    setBatchSchoolModalVisible(true);
  };

  const handleBatchSetSchoolSubmit = () => {
    const values = batchSchoolForm.getFieldsValue();
    if (!values.school_id) {
      message.warning('请选择学校');
      return;
    }
    batchSetSchoolMutation.mutate({
      user_ids: selectedRowKeys as number[],
      school_id: values.school_id,
    });
  };

  // 批量重置密码
  const handleBatchResetPassword = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请至少选择一个用户');
      return;
    }
    setBatchPasswordModalVisible(true);
  };

  const handleBatchResetPasswordSubmit = () => {
    const values = batchPasswordForm.getFieldsValue();
    const autoGenerate = values.auto_generate || false;
    const password = autoGenerate ? undefined : values.password;

    if (!autoGenerate && !password) {
      message.warning('请输入密码或选择自动生成');
      return;
    }

    if (!autoGenerate && password && password.length < 6) {
      message.warning('密码长度不能少于6位');
      return;
    }

    batchResetPasswordMutation.mutate({
      user_ids: selectedRowKeys as number[],
      password,
    });
  };

  // 切换用户（系统管理员专用）
  const handleSwitchUser = () => {
    setSwitchModalVisible(true);
  };

  const handleSwitchSubmit = async (targetUserId: number) => {
    try {
      await api.get('/users/switch_user', {
        params: { target_user_id: targetUserId }
      });
      message.success('切换用户成功');
      setSwitchModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      // 重新获取当前用户信息
      await fetchUser();
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail;
      let errorMessage = '切换用户失败';
      if (typeof errorDetail === 'string') {
        errorMessage = errorDetail;
      } else if (Array.isArray(errorDetail) && errorDetail.length > 0) {
        errorMessage = errorDetail[0].msg || errorMessage;
      }
      message.error(errorMessage);
    }
  };

  const handleCancelSwitch = async () => {
    try {
      await api.get('/users/cancel_switch');
      message.success('已恢复系统管理员身份');
      setSwitchModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['users', 'me'] });
      setSwitchTargetUser(null);
      // 重新获取当前用户信息
      await fetchUser();
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail;
      let errorMessage = '取消切换失败';
      if (typeof errorDetail === 'string') {
        errorMessage = errorDetail;
      } else if (Array.isArray(errorDetail) && errorDetail.length > 0) {
        errorMessage = errorDetail[0].msg || errorMessage;
      }
      message.error(errorMessage);
    }
  };

  // 学校管理相关函数
  const handleCreateSchool = () => {
    setSelectedSchoolForManage(null);
    setSchoolModalType('create');
    setSchoolModalVisible(true);
    schoolForm.resetFields();
  };

  const handleEditSchool = (school: School) => {
    setSelectedSchoolForManage(school);
    setSchoolModalType('edit');
    setSchoolModalVisible(true);
    schoolForm.setFieldsValue({
      name: school.name,
    });
  };

  const handleDeleteSchool = (schoolId: number) => {
    deleteSchoolMutation.mutate(schoolId);
  };

  const handleSchoolSubmit = () => {
    const values = schoolForm.getFieldsValue();
    if (selectedSchoolForManage) {
      updateSchoolMutation.mutate({ schoolId: selectedSchoolForManage.id, values });
    } else {
      createSchoolMutation.mutate(values);
    }
  };

  // 学校管理表格列
  const schoolColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '学校名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '用户数量',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 120,
      render: (count: number) => count || 0,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDateToLocalZh(date) || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: School) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => handleEditSchool(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title={`确定要删除学校"${record.name}"吗？`}
            description="删除学校将同时删除该学校下的所有用户和相关数据"
            onConfirm={() => handleDeleteSchool(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (text: string) => (
        <Space>
          {text}
          {user?.id === selectedUser?.id && <SwapOutlined style={{ marginLeft: 8, cursor: 'pointer', color: '#1890ff' }} onClick={handleSwitchUser} />}
        </Space>
      ),
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
      render: (date: string) => formatDateToLocalZh(date) || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: Student) => {
        const canEdit = user?.role === 'system_admin' ||
                         (user?.role === 'school_admin' && user.school_id === record.school_id);
        // 不能删除自己，也不能删除系统管理员
        const canDelete = user?.role === 'system_admin' &&
                            record.id !== user.id &&
                            record.role !== 'system_admin';
        // 不能修改系统管理员的密码
        const canChangePassword = user?.role === 'system_admin' &&
                                record.id !== user.id &&
                                record.role !== 'system_admin';
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
            {canChangePassword && (
              <Button
                type="link"
                size="small"
                icon={<LockOutlined />}
                onClick={() => handleChangePassword(record)}
              >
                修改密码
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
            {!canDelete && (
              <Button
                type="link"
                size="small"
                danger
                disabled
                title={
                  user && record.id === user.id
                    ? '不能删除自己'
                    : record.role === 'system_admin'
                    ? '不能删除系统管理员'
                    : '无权删除此用户'
                }
              >
                删除
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <h1>{activeTab === 'schools' ? '学校管理' : '用户管理'}</h1>

      {/* 标签页切换 - 仅系统管理员可见 */}
      {user?.role === 'system_admin' && (
        <Card style={{ marginBottom: 16 }}>
          <Tabs
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as 'users' | 'schools')}
            items={[
              {
                key: 'users',
                label: '用户管理',
              },
              {
                key: 'schools',
                label: '学校管理',
              },
            ]}
          />
        </Card>
      )}

      {/* 切换状态提示 */}
      {user?.is_switched && (
        <Alert
          message="当前已切换为其他用户"
          description={
            <Space>
              <span>您正在以 {user.nickname || user.username} 的身份操作</span>
              <Button type="primary" size="small" onClick={handleCancelSwitch}>
                恢复管理员身份
              </Button>
            </Space>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          closable={false}
        />
      )}

      {/* 用户管理标签页内容 */}
      {activeTab === 'users' && (
        <>
          {/* 学校管理员和系统管理员可以筛选学校 */}
          {(user?.role === 'school_admin' || (user?.role === 'system_admin' && !user?.is_switched)) && schools && (
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
            <Space direction="vertical" size="middle">
              {/* 第一行按钮 */}
              <Space size="middle" wrap>
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
                <Button icon={<ExportOutlined />} onClick={handleExport}>
                  导出名单
                </Button>
                {user?.role === 'system_admin' && !user?.is_switched && (
                  <Button icon={<SwapOutlined />} onClick={handleSwitchUser}>
                    切换用户
                  </Button>
                )}
              </Space>
              {/* 第二行：批量操作按钮 */}
              {selectedRowKeys.length > 0 && (
                <Space size="middle" wrap>
                  {user?.role === 'system_admin' && (
                    <Button
                      icon={<SwapOutlined />}
                      onClick={handleBatchSetSchool}
                      loading={batchSetSchoolMutation.isPending}
                    >
                      批量设置学校
                    </Button>
                  )}
                  {user?.role === 'system_admin' && (
                    <Button
                      icon={<LockOutlined />}
                      onClick={handleBatchResetPassword}
                      loading={batchResetPasswordMutation.isPending}
                    >
                      批量重置密码
                    </Button>
                  )}
                  <Popconfirm
                    title={`确定要删除选中的 ${selectedRowKeys.length} 个用户吗？`}
                    onConfirm={handleBatchDelete}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      loading={batchDeleteMutation.isPending}
                    >
                      批量删除
                    </Button>
                  </Popconfirm>
                </Space>
              )}
            </Space>
          </Card>

          {/* 用户列表 */}
          <Card>
            <Table
              columns={columns}
              dataSource={filteredUsers}
              loading={isLoading}
              rowKey="id"
              rowSelection={{
                selectedRowKeys,
                onChange: (selectedRowKeys: React.Key[]) => {
                  setSelectedRowKeys(selectedRowKeys);
                },
                getCheckboxProps: (record: Student) => ({
                  // 系统管理员可以删除所有用户，学校管理员只能删除本校用户
                  disabled: user?.role !== 'system_admin' && (user?.role === 'school_admin' && record.school_id !== user.school_id),
                }),
              }}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 人`,
              }}
            />
          </Card>
        </>
      )}

      {/* 学校管理标签页内容 - 仅系统管理员 */}
      {activeTab === 'schools' && user?.role === 'system_admin' && (
        <>
          {/* 操作按钮 */}
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSchool}>
                创建学校
              </Button>
            </Space>
          </Card>

          {/* 学校列表 */}
          <Card>
            <Table
              columns={schoolColumns}
              dataSource={schoolsWithUsers}
              loading={schoolsLoading}
              rowKey="id"
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 所学校`,
              }}
            />
          </Card>
        </>
      )}

      {/* 创建/批量创建/导入/编辑/修改密码 模态框 */}
      <Modal
        title={modalType === 'batch' ? '批量创建学生' : modalType === 'import' ? '导入学生名单' : modalType === 'edit' ? '编辑用户' : modalType === 'password' ? '修改密码' : '创建用户'}
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
          ) : modalType === 'password' ? (
            <Button
              key="submit"
              type="primary"
              onClick={() => form.submit()}
              loading={changePasswordMutation.isPending}
            >
              修改密码
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
        <Tabs activeKey={modalType === 'edit' || modalType === 'password' ? 'create' : modalType} onChange={(key) => {
          if (key !== 'edit' && key !== 'password') {
            setModalType(key as any);
          }
        }}>
          <TabPane tabKey="create" key="create">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
            >
              {modalType === 'password' ? (
                <>
                  <Form.Item name="password" label="新密码" rules={[{ required: true, min: 6 }]}>
                    <Input.Password placeholder="请输入新密码（至少6位）" />
                  </Form.Item>
                  <Form.Item name="confirmPassword" label="确认密码" rules={[
                    { required: true },
                    ({ getFieldValue }) => ({
                      validator: (_, value) => {
                        if (value && value !== getFieldValue('password')) {
                          return Promise.reject('两次输入的密码不一致');
                        }
                        return Promise.resolve();
                      },
                    }),
                  ]}>
                    <Input.Password placeholder="请再次输入新密码" />
                  </Form.Item>
                </>
              ) : (
                <>
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
                </>
              )}
            </Form>
          </TabPane>

          <TabPane tabKey="batch" key="batch">
            <Form form={batchForm} layout="vertical" initialValues={{ students: [{ username: '', nickname: '', password: '', school_id: user?.school_id }], auto_generate_username: false, auto_generate_password: false }}>
              <Alert
                message="批量创建说明"
                description="可以手动输入学生信息，也可以自动生成学号和密码。系统管理员可以为不同学校创建学生。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              {user?.role === 'system_admin' && (
                <Alert
                  message="学校选择说明"
                  description="如果不选择学校，将根据批量创建按钮的上下文确定学校。建议明确选择学校以避免混淆。"
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}
              {user?.role === 'system_admin' && schools && (
                <Form.Item name="batch_school_id" label="学校（可选）">
                  <Select
                    placeholder="请选择学校（留空则默认为所选学校）"
                    allowClear
                    onChange={(value) => {
                      // 更新表单中所有学生的 school_id
                      const currentStudents = batchForm.getFieldValue('students') || [];
                      batchForm.setFieldValue('students', currentStudents.map((s: BatchStudentData) => ({
                        ...s,
                        school_id: value || user.school_id
                      })));
                    }}
                  >
                    {schools.map((school: School) => (
                      <Select.Option key={school.id} value={school.id}>
                        {school.name}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              )}
              <Form.Item name="auto_generate_username" valuePropName="checked">
                <span>自动生成学号（格式：2024XXXX）</span>
              </Form.Item>
              <Form.Item name="auto_generate_password" valuePropName="checked">
                <span>自动生成密码（8位，包含字母和数字）</span>
              </Form.Item>
              <Form.List name="students">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map((field) => (
                      <Space key={field.key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                        <Form.Item
                          name={[field.name, 'username']}
                          rules={[{ required: true }]}
                          style={{ marginBottom: 0, width: 130 }}
                        >
                          <Input placeholder="学号（或留空自动生成）" />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'nickname']}
                          rules={[{ required: true }]}
                          style={{ marginBottom: 0, width: 130 }}
                        >
                          <Input placeholder="姓名" />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'password']}
                          style={{ marginBottom: 0, width: 130 }}
                        >
                          <Input.Password placeholder="密码（或留空自动生成）" />
                        </Form.Item>
                        {user?.role === 'system_admin' && (
                          <Form.Item
                            name={[field.name, 'school_id']}
                            style={{ marginBottom: 0, width: 130 }}
                          >
                            <Select
                              placeholder="学校（可选）"
                              allowClear
                            >
                              {schools?.map((school: School) => (
                                <Select.Option key={school.id} value={school.id}>
                                  {school.name}
                                </Select.Option>
                              ))}
                            </Select>
                          </Form.Item>
                        )}
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
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    <li>请上传Excel文件，文件应包含以下列：学号、姓名（昵称）、密码。</li>
                    <li>如果不包含密码，将使用自动生成的密码。</li>
                    {user?.role === 'system_admin' && (
                      <li>可以添加"学校"列来指定学生所属学校（可选）。</li>
                    )}
                    {user?.role === 'school_admin' && (
                      <li>如果不指定学校，将默认为您所在的学校。</li>
                    )}
                  </ul>
                }
                type="info"
                showIcon
              />
              {user?.role === 'system_admin' && schools && (
                <Form.Item label="默认学校（可选）">
                  <Select
                    placeholder="选择默认学校（可选）"
                    allowClear
                    onChange={(value) => {
                      batchForm.setFieldValue('batch_school_id', value);
                    }}
                  >
                    {schools.map((school: School) => (
                      <Select.Option key={school.id} value={school.id}>
                        {school.name}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              )}
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

      {/* 导出筛选弹窗 */}
      <Modal
        title="导出用户名单"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        onOk={handleExportSubmit}
        okText="导出"
        okButtonProps={{ loading: exportMutation.isPending }}
        width={600}
      >
        <Form layout="vertical">
          <Form.Item label="学校筛选">
            <Select
              placeholder="全部学校"
              allowClear
              value={exportFilters.school_id}
              onChange={(value) => setExportFilters({ ...exportFilters, school_id: value })}
              disabled={user?.role === 'school_admin' || user?.role === 'teacher'}
            >
              {schools?.map((school: School) => (
                <Select.Option key={school.id} value={school.id}>
                  {school.name}
                </Select.Option>
              ))}
            </Select>
            {user?.role === 'school_admin' && (
              <Alert
                message="学校管理员权限限制"
                description="您只能导出本校的用户名单"
                type="info"
                style={{ marginTop: 8 }}
              />
            )}
          </Form.Item>
          <Form.Item label="角色筛选">
            <Select
              placeholder="全部角色"
              allowClear
              value={exportFilters.role}
              onChange={(value) => setExportFilters({ ...exportFilters, role: value })}
            >
              <Select.Option value="student">学生</Select.Option>
              <Select.Option value="teacher">教师</Select.Option>
              <Select.Option value="school_admin">学校管理员</Select.Option>
            </Select>
          </Form.Item>
          <Alert
            message="导出说明"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>默认导出所有学生用户</li>
                <li>可以按学校和角色进行筛选导出</li>
                <li>学校管理员和教师只能导出本校的用户</li>
                <li>系统管理员可以导出所有学校的用户</li>
              </ul>
            }
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* 切换用户弹窗（系统管理员专用） */}
      <Modal
        title="切换用户身份"
        open={switchModalVisible}
        onCancel={() => {
          setSwitchModalVisible(false);
          setSwitchTargetUser(null);
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            handleCancelSwitch();
          }}>
            取消
          </Button>,
          <Button key="switch" type="primary" onClick={() => {
            if (switchTargetUser) {
              handleSwitchSubmit(switchTargetUser.id);
            }
          }} disabled={!switchTargetUser}>
            确认切换
          </Button>,
          <Button
            key="recover"
            danger
            onClick={handleCancelSwitch}
            icon={<LogoutOutlined />}
          >
            恢复身份
          </Button>
        ]}
        width={600}
      >
        <Alert
          message="身份切换说明"
          description={
            <div style={{ lineHeight: 1.6 }}>
              <p><strong>系统管理员快速切换用户功能</strong></p>
              <ul style={{ margin: '16px 0 0 0 20px', paddingLeft: 20 }}>
                <li>切换后，系统管理员将临时以目标用户的身份操作</li>
                <li>批量创建学生时将使用切换后的用户所属学校</li>
                <li>可以随时恢复为系统管理员身份</li>
                <li><strong style={{ color: 'red' }}>注意：此功能仅用于测试和特定场景</strong></li>
              </ul>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Divider />

        <Form layout="vertical">
          <Form.Item label="选择要切换的用户">
            <Select
              placeholder="请选择用户"
              showSearch
              optionFilterProp="children"
              value={switchTargetUser?.id || undefined}
              onChange={(value) => {
                const targetUser = users?.find((u: Student) => u.id === value);
                setSwitchTargetUser(targetUser || null);
              }}
              notFoundContent="未找到用户"
              filterOption={(input, option) =>
                option?.nickname?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {users?.map((userItem: Student) => (
                <Select.Option key={userItem.id} value={userItem.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{userItem.nickname || userItem.username}</div>
                      <div style={{ color: '#999', fontSize: 12 }}>
                        @{userItem.username} ({userItem.role})
                      </div>
                    </div>
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              danger
              onClick={handleCancelSwitch}
              icon={<LogoutOutlined />}
            >
              立即恢复系统管理员身份
            </Button>
          </Form.Item>

          <Alert
            message="权限说明"
            description={`切换后将以用户 ${switchTargetUser?.nickname || switchTargetUser?.username || '...'} (ID: ${switchTargetUser?.id}) 的身份进行操作`}
            type="info"
          />
        </Form>
      </Modal>

      {/* 学校管理 - 创建/编辑 模态框 */}
      <Modal
        title={schoolModalType === 'create' ? '创建学校' : '编辑学校'}
        open={schoolModalVisible}
        onCancel={() => {
          setSchoolModalVisible(false);
          setSelectedSchoolForManage(null);
          schoolForm.resetFields();
        }}
        onOk={handleSchoolSubmit}
        okText={schoolModalType === 'create' ? '创建' : '更新'}
        confirmLoading={createSchoolMutation.isPending || updateSchoolMutation.isPending}
      >
        <Form form={schoolForm} layout="vertical">
          <Form.Item
            name="name"
            label="学校名称"
            rules={[
              { required: true, message: '请输入学校名称' },
              { max: 100, message: '学校名称不能超过100个字符' },
            ]}
          >
            <Input placeholder="请输入学校名称" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量设置学校模态框 */}
      <Modal
        title={`批量设置学校 (${selectedRowKeys.length} 个用户)`}
        open={batchSchoolModalVisible}
        onCancel={() => {
          setBatchSchoolModalVisible(false);
          batchSchoolForm.resetFields();
        }}
        onOk={handleBatchSetSchoolSubmit}
        okText="确定"
        okButtonProps={{ loading: batchSetSchoolMutation.isPending }}
      >
        <Alert
          message="批量设置学校说明"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>将为选中的 {selectedRowKeys.length} 个用户设置相同的学校</li>
              <li>不能修改系统管理员的学校</li>
              <li>请谨慎操作，确认无误后再提交</li>
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={batchSchoolForm} layout="vertical">
          <Form.Item
            name="school_id"
            label="选择学校"
            rules={[{ required: true, message: '请选择学校' }]}
          >
            <Select
              placeholder="请选择学校"
              showSearch
              optionFilterProp="children"
            >
              {schools?.map((school: School) => (
                <Select.Option key={school.id} value={school.id}>
                  {school.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量重置密码模态框 */}
      <Modal
        title={`批量重置密码 (${selectedRowKeys.length} 个用户)`}
        open={batchPasswordModalVisible}
        onCancel={() => {
          setBatchPasswordModalVisible(false);
          batchPasswordForm.resetFields();
        }}
        onOk={handleBatchResetPasswordSubmit}
        okText="确定并下载结果"
        okButtonProps={{ loading: batchResetPasswordMutation.isPending }}
      >
        <Alert
          message="批量重置密码说明"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>将为选中的 {selectedRowKeys.length} 个用户重置密码</li>
              <li>不能重置系统管理员的密码</li>
              <li>不能重置自己的密码</li>
              <li>操作完成后会自动下载包含新密码的Excel表格</li>
              <li>请妥善保存下载的密码表格，确认无误后再提交</li>
            </ul>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={batchPasswordForm} layout="vertical">
          <Form.Item name="auto_generate" valuePropName="checked" initialValue={true}>
            <span>自动生成密码（8位，包含字母和数字）</span>
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.auto_generate !== currentValues.auto_generate
            }
          >
            {({ getFieldValue }) =>
              !getFieldValue('auto_generate') ? (
                <Form.Item
                  name="password"
                  label="新密码"
                  rules={[
                    { required: true, message: '请输入新密码' },
                    { min: 6, message: '密码长度不能少于6位' },
                  ]}
                >
                  <Input.Password placeholder="请输入新密码（至少6位）" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement;
