# 用户管理页面功能改进文档

## 改进概述

本次实现的功能包括：
1. **修改用户信息**：已存在，保持不变
2. **修改用户密码**：新增功能，允许管理员修改用户密码
3. **删除用户**：已存在，保持不变
4. **导出名单弹窗**：改进为带筛选的弹窗，支持按学校和角色筛选
5. **批量删除用户**：新增功能，支持勾选多个用户并批量删除

## 修改的文件

### `frontend/src/pages/UserManagement.tsx`

#### 1. 导入新的组件和图标

```typescript
import { LockOutlined } from '@ant-design/icons';
```

#### 2. 新增状态管理

```typescript
const [exportModalVisible, setExportModalVisible] = useState(false);
const [exportFilters, setExportFilters] = useState<{
  school_id?: number;
  role?: string;
}>({});
const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
```

#### 3. 新增批量删除Mutation

```typescript
const batchDeleteMutation = useMutation({
  mutationFn: async (userIds: number[]) => {
    await Promise.all(userIds.map(id => api.delete(`/users/${id}`)));
  },
  onSuccess: () => {
    message.success(`成功删除 ${selectedRowKeys.length} 个用户`);
    setSelectedRowKeys([]);
    queryClient.invalidateQueries({ queryKey: ['users'] });
  },
  onError: () => {
    message.error('批量删除失败');
  },
});
```

#### 4. 新增修改密码Mutation

```typescript
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
```

#### 5. 改进导出功能

```typescript
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
    setExportModalVisible(false);
  },
  onError: () => {
    message.error('导出失败');
  },
});
```

#### 6. 新增处理函数

```typescript
// 处理修改密码
const handleChangePassword = (user: Student) => {
  setSelectedUser(user);
  setModalType('password');
  setModalVisible(true);
  form.resetFields();
};

// 处理导出（打开筛选弹窗）
const handleExport = () => {
  setExportModalVisible(true);
  // 根据当前用户权限设置默认筛选
  if (user?.role === 'school_admin') {
    setExportFilters({
      school_id: user.school_id,
      role: 'student'
    });
  } else if (user?.role === 'teacher') {
    setExportFilters({
      school_id: user.school_id,
      role: 'student'
    });
  } else {
    setExportFilters({ role: 'student' });
  }
};

// 批量删除
const handleBatchDelete = () => {
  if (selectedRowKeys.length === 0) {
    message.warning('请至少选择一个用户');
    return;
  }
  batchDeleteMutation.mutate(selectedRowKeys as number[]);
};
```

#### 7. 更新操作列

在表格的"操作"列中添加"修改密码"按钮：

```typescript
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
```

#### 8. 添加批量删除按钮

```typescript
{selectedRowKeys.length > 0 && (
  <Popconfirm
    title={`确定要删除选中的 ${selectedRowKeys.length} 个用户吗？`}
    onConfirm={handleBatchDelete}
    okText="确定"
    cancelText="取消"
  >
    <Button danger icon={<DeleteOutlined />} loading={batchDeleteMutation.isPending}>
      批量删除
    </Button>
  </Popconfirm>
)}
```

#### 9. 添加表格行选择

```typescript
<Table
  ...
  rowSelection={{
    selectedRowKeys,
    onChange: (keys: React.Key[], rows: Student[], info: { type: 'all' | 'none' }) => {
      setSelectedRowKeys(keys);
    },
    getCheckboxProps: (record: Student) => ({
      // 系统管理员可以删除所有用户，学校管理员只能删除本校用户
      disabled: user?.role !== 'system_admin' && (user?.role === 'school_admin' && record.school_id !== user.school_id),
    }),
  }}
/>
```

#### 10. 添加导出筛选弹窗

```typescript
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
  </Form>
</Modal>
```

#### 11. 添加修改密码表单

```typescript
{modalType === 'password' ? (
  <>
    <Form.Item name="password" label="新密码" rules={[{ required: true, min: 6 }]}>
      <Input.Password placeholder="请输入新密码（至少6位）" />
    </Form.Item>
    <Form.Item name="confirmPassword" label="确认密码" rules={[
      { required: true },
      ({ getFieldValue }) => ({
        validator(_, value) {
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
  // 原有的创建/编辑表单
  ...
)}
```

## 功能说明

### 1. 修改用户信息

**保持不变**：点击"编辑"按钮打开编辑模态框，可以修改用户名、昵称、角色和学校。

### 2. 修改用户密码

**新增功能**：
- 在操作列中添加"修改密码"按钮
- 点击后打开密码修改模态框
- 输入新密码和确认密码
- 提交后调用 `/users/{id}` API，只更新密码字段

**权限控制**：
- 系统管理员可以修改所有用户的密码
- 学校管理员可以修改本校用户的密码

### 3. 删除用户

**保持不变**：点击"删除"按钮，确认后删除用户。

**权限控制**：
- 只有系统管理员可以删除用户

### 4. 导出名单

**改进功能**：
- 点击"导出名单"按钮打开筛选弹窗
- 可以选择导出哪个学校的用户
- 可以选择导出哪个角色的用户
- 支持导出全部或筛选后的结果

**权限控制**：
- 系统管理员可以导出所有学校的用户
- 学校管理员只能导出本校的用户
- 教师只能导出本校的学生

**默认筛选**：
- 学校管理员默认导出本校的学生
- 教师默认导出本校的学生
- 系统管理员默认导出所有学生

### 5. 批量删除用户

**新增功能**：
- 在表格左侧添加复选框
- 支持单选和全选
- 选中用户后显示"批量删除"按钮
- 点击"批量删除"并确认后，批量删除选中的用户

**权限控制**：
- 系统管理员可以删除所有用户
- 学校管理员只能删除本校用户（复选框会被禁用）

## API 接口

### 修改密码

```
PUT /api/users/{user_id}
Body: {
  "password": "new_password"
}
```

### 批量删除

```
DELETE /api/users/{user_id}
多次调用
```

### 导出（支持筛选）

```
GET /api/users/export?school_id={school_id}&role={role}
返回：Excel 文件
```

## UI 改进

### 1. 导出按钮改进

**之前**：点击"导出学生名单"直接下载

**现在**：点击"导出名单"打开筛选弹窗，可以选择筛选条件后再导出

### 2. 操作列改进

**之前**：只有"编辑"和"删除"按钮

**现在**：添加了"修改密码"按钮

### 3. 表格改进

**之前**：没有行选择功能

**现在**：添加了行选择（复选框），支持批量操作

### 4. 按钮区域改进

**之前**：只有"创建用户"等按钮

**现在**：添加了"批量删除"按钮（只在有选中用户时显示）

## 权限矩阵

| 功能 | 系统管理员 | 学校管理员 | 教师 | 学生 |
|------|-----------|-----------|------|------|
| 修改用户信息 | 所有用户 | 本校用户 | 无 | 无 |
| 修改用户密码 | 所有用户 | 本校用户 | 无 | 无 |
| 删除用户 | 所有用户 | 无 | 无 | 无 |
| 批量删除 | 所有用户 | 无 | 无 | 无 |
| 导出全部名单 | 所有学校 | 本校 | 本校学生 | 无 |
| 导出筛选名单 | 所有学校 | 本校 | 本校学生 | 无 |

## 测试建议

### 1. 修改用户信息
1. 点击某个用户的"编辑"按钮
2. 修改昵称和角色
3. 点击"确定"
4. 验证修改成功

### 2. 修改用户密码
1. 点击某个用户的"修改密码"按钮
2. 输入新密码
3. 输入确认密码（应该与新密码一致）
4. 点击"修改密码"
5. 验证密码修改成功

### 3. 导出名单
1. 点击"导出名单"按钮
2. 在弹窗中选择学校和角色筛选
3. 点击"导出"
4. 验证下载的Excel文件包含筛选后的用户

### 4. 批量删除用户
1. 在表格中勾选多个用户
2. 点击"批量删除"按钮
3. 确认删除
4. 验证所有选中的用户都被删除

## 注意事项

1. **密码验证**：修改密码时需要两次输入密码，确保一致性
2. **权限提示**：在导出弹窗中显示权限限制提示
3. **批量操作反馈**：批量删除成功后显示删除的用户数量
4. **复选框状态管理**：删除或刷新列表后，清空选中的用户
