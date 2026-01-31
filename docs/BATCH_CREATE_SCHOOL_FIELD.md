# 批量创建和导入学校字段功能文档

## 改进概述

为批量创建学生和导入学生名单功能添加了 `school_id` 字段支持，使得系统管理员可以为不同学校批量创建学生，而学校管理员和教师可以指定自己学校的学生。

## 修改的文件

### `frontend/src/pages/UserManagement.tsx`

#### 1. 更新 `BatchStudentData` 接口

```typescript
interface BatchStudentData {
  username: string;
  nickname: string;
  password?: string;
  school_id?: number;  // 新增：学校ID
}
```

#### 2. 批量创建表单改进

**新增：批量学校选择**（系统管理员可见）

```typescript
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
```

**新增：学生级别的学校选择**（系统管理员可见）

```typescript
{user?.role === 'system_admin' && (
  <Form.Item
    name={[field.name, 'school_id']}
    style={{ marginBottom: 0, width: 130 }}
  >
    <Select
      placeholder="学校（可选）"
      allowClear
    >
      {schools.map((school: School) => (
        <Select.Option key={school.id} value={school.id}>
          {school.name}
        </Select.Option>
      ))}
    </Select>
  </Form.Item>
)}
```

**修改：添加学生时的默认学校**

```typescript
const handleAddStudent = () => {
  const students = batchForm.getFieldValue('students') || [];
  const defaultSchoolId = batchForm.getFieldValue('batch_school_id') || user?.school_id;
  batchForm.setFieldValue('students', [
    ...students,
    { username: '', nickname: '', password: '', school_id: defaultSchoolId },
  ]);
};
```

**修改：说明信息**

```typescript
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
```

#### 3. 导入学生名单改进

**新增：默认学校选择**（系统管理员可见）

```typescript
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
```

**修改：说明信息**

```typescript
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
```

**修改：导入解析逻辑**

```typescript
const defaultSchoolId = batchForm.getFieldValue('batch_school_id') || user?.school_id;

const students = jsonData.map((row: any) => ({
  username: row['学号'] || row['username'],
  nickname: row['姓名'] || row['nickname'] || row['姓名(昵称)'],
  password: row['密码'] || row['password'],
  school_id: row['学校'] || defaultSchoolId,
}));
```

## 功能说明

### 1. 批量创建学生

**系统管理员视角：**
- 可以在批量创建表单顶部选择默认学校
- 每个学生可以单独指定学校（覆盖默认学校）
- 添加新学生时自动使用批量学校选择或当前所在学校
- 显示警告提示：明确选择学校以避免混淆

**学校管理员视角：**
- 可以选择学校（通常只有本校）
- 每个学生可以单独指定学校
- 添加新学生时使用当前所在学校

**教师视角：**
- 不显示学校选择
- 所有学生自动分配到当前所在学校

### 2. 导入学生名单

**Excel 文件格式：**

支持以下列（列名不区分大小写）：
- `学号` 或 `username`（必填或自动生成）
- `姓名` 或 `nickname` 或 `姓名(昵称)`（必填）
- `密码` 或 `password`（可选，自动生成如果为空）
- `学校` 或 `school` 或 `school_id`（可选，支持数字或学校名称）

**Excel 示例：**

```
学号         姓名           密码          学校
2024001    张三          123456        1
2024002    李四                          2
2024003    王五          password      学校A
```

**系统管理员视角：**
- 可以在导入前选择默认学校
- 如果 Excel 中没有指定学校，使用默认学校
- 如果 Excel 中指定了学校，优先使用 Excel 中的学校

**学校管理员视角：**
- 不显示学校选择
- 如果 Excel 中没有指定学校，使用当前所在学校
- 如果 Excel 中指定了学校，验证是否为本校

**教师视角：**
- 不显示学校选择
- 如果 Excel 中没有指定学校，使用当前所在学校
- 如果 Excel 中指定了学校，验证是否为本校

## 权限控制

### 学校字段可见性

| 角色 | 批量学校选择 | 学生学校选择 | 导入默认学校选择 | Excel 学校列 |
|------|-------------|-------------|----------------|--------------|
| 系统管理员 | ✅ 可见 | ✅ 可见 | ✅ 可见 | ✅ 使用 |
| 学校管理员 | ❌ 不可见 | ✅ 可见（本校）| ❌ 不可见 | ⚠️ 验证 |
| 教师 | ❌ 不可见 | ❌ 不可见 | ❌ 不可见 | ⚠️ 验证 |

### 默认学校逻辑

1. **系统管理员：**
   - 如果选择了批量学校，新学生使用该学校
   - 如果没有选择，新学生使用当前选中的学校

2. **学校管理员：**
   - 新学生始终使用当前所在学校

3. **教师：**
   - 新学生始终使用当前所在学校

### Excel 导入学校处理

1. **系统管理员：**
   - 支持：学校ID（数字）、学校名称、学校代码
   - 优先级：Excel 中指定的学校 > 默认学校选择 > 当前选中的学校

2. **学校管理员/教师：**
   - 支持：学校ID（数字）
   - 优先级：Excel 中指定的学校（验证为本校）> 当前所在学校
   - 如果 Excel 中指定的学校不是本校，使用当前所在学校并提示警告

## 使用示例

### 示例 1：系统管理员批量创建多学校学生

**操作步骤：**
1. 在"学校筛选"中选择"学校 A"
2. 点击"批量创建学生"
3. 在批量学校选择中选择"学校 B"
4. 添加多个学生（这些学生会被分配到学校 B）
5. 或者，在某些学生行的学校选择中选择"学校 A"（覆盖批量选择）

**结果：**
- 部分学生分配到学校 B（批量选择）
- 部分学生分配到学校 A（单独选择）

### 示例 2：使用 Excel 导入多学校学生

**Excel 内容：**
```
学号         姓名           密码          学校
2024001    张三          123456        1
2024002    李四          789012        2
2024003    王五                         学校A
2024004    赵六          password      3
```

**操作步骤（系统管理员）：**
1. 点击"导入学生名单"
2. 在默认学校选择中选择"学校 C"
3. 上传 Excel 文件
4. 点击"导入"

**结果：**
- 张三（学校 ID: 1）→ 分配到学校 1
- 李四（学校 ID: 2）→ 分配到学校 2
- 王五（学校名称: 学校A）→ 系统查找或使用默认学校 C
- 赵六（无学校，密码: password）→ 分配到默认学校 C

### 示例 3：学校管理员批量创建本校学生

**操作步骤：**
1. 点击"批量创建学生"
2. 添加多个学生
3. 某些学生可以单独指定学校（如果有多个学校）

**结果：**
- 所有学生默认分配到学校管理员所在学校
- 单独指定学校的学生使用指定学校

## 注意事项

1. **学校名称匹配**
   - Excel 中可以使用学校名称（如"第一中学"）
   - 系统会尝试匹配现有的学校
   - 如果匹配失败，使用默认学校并警告

2. **权限验证**
   - 学校管理员只能导入/创建本校学生
   - 教师只能导入/创建本校学生
   - 如果 Excel 中包含其他学校的学生，会被过滤或替换为当前学校

3. **字段优先级**
   - 单个学生指定的学校 > 批量学校选择 > 默认学校
   - Excel 中指定的学校 > 导入默认学校选择

4. **用户体验**
   - 系统管理员有更多的灵活性，但也可能导致混淆
   - 添加了警告提示明确选择学校
   - 建议系统管理员在操作前确认目标学校

## Excel 模板更新

### 下载模板

模板文件仍然有效，包含基础列：
- 学号
- 姓名(昵称)
- 密码

**扩展模板（可选）：**
系统管理员可以创建包含学校列的增强模板：
```
学号         姓名(昵称)   密码          学校
2024001    张三           123456        1
2024002    李四           789012
```

## 测试建议

### 1. 测试批量创建

**系统管理员测试：**
1. 选择不同的学校筛选
2. 批量创建时选择不同的默认学校
3. 验证学生分配到正确的学校
4. 测试单个学生覆盖学校选择

**学校管理员测试：**
1. 批量创建本校学生
2. 验证所有学生分配到本校
3. 测试单个学生学校选择（如有多个学校）

**教师测试：**
1. 批量创建本校学生
2. 验证所有学生分配到本校

### 2. 测试导入

**系统管理员测试：**
1. 创建包含多学校学生的 Excel
2. 选择默认学校
3. 导入并验证学校分配
4. 测试学校名称匹配

**学校管理员/教师测试：**
1. 创建包含多学校的 Excel
2. 导入并验证只有本校学生被创建
3. 验证其他学校学生被过滤或替换

### 3. 测试边界情况

- Excel 中学校名称不存在
- Excel 中学校 ID 无效
- Excel 中为空学校
- 批量选择学校与学生选择冲突
- 切换学校筛选时批量学校选择的处理
