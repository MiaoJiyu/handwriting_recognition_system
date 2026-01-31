# 系统管理员快速切换用户功能文档

## 功能概述

为系统管理员提供了快速切换用户身份的功能，使系统管理员可以临时以其他用户的身份操作，比如为不同学校批量创建学生。

## 修改的文件

### 1. 后端数据库模型

#### `backend/app/models/user.py`

**新增字段：**
```python
# 系统管理员切换功能
switched_user_id = Column(Integer, nullable=True)
switched_to_username = Column(String(50), nullable=True)
switched_at = Column(DateTime(timezone=True), nullable=True)
```

#### `backend/app/models/audit_log.py`

**新增文件**：审计日志模型

**字段：**
- `id`：日志ID
- `actor_id`：操作者ID（系统管理员）
- `target_user_id`：目标用户ID
- `action_type`：操作类型（login, logout, switch_user, cancel_switch）
- `details`：操作详情
- `ip_address`：IP地址
- `created_at`：创建时间

### 2. 后端API

#### `backend/app/api/users.py`

**新增API端点：**

#### 1. 切换到指定用户（系统管理员专用）

```python
@router.get("/switch_user", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def switch_user(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """系统管理员切换到指定用户"""
    # 获取目标用户
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在"
        )

    # 检查目标用户是否为系统管理员
    if target_user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能切换到系统管理员"
        )

    # 更新当前用户的切换状态
    current_user.switched_user_id = target_user_id
    current_user.switched_to_username = target_user.username
    current_user.switched_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    db.refresh(target_user)

    # 记录切换日志
    from ..models.audit_log import AuditLog
    audit_log = AuditLog(
        actor_id=current_user.id,
        action="switch_user",
        target_user_id=target_user_id,
        target_username=target_user.username,
        details=f"系统管理员 {current_user.username} 切换到用户 {target_user.username} (ID:{target_user_id})",
        ip_address=None  # 可以从请求头获取
    )
    db.add(audit_log)
    db.commit()

    return target_user
```

#### 2. 取消切换，恢复系统管理员身份

```python
@router.get("/cancel_switch", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def cancel_switch(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """取消切换用户，恢复系统管理员身份"""
    # 重置切换状态
    current_user.switched_user_id = None
    current_user.switched_to_username = None
    current_user.switched_at = None
    db.commit()
    db.refresh(current_user)

    # 记录取消切换日志
    from ..models.audit_log import AuditLog
    audit_log = AuditLog(
        actor_id=current_user.id,
        action="cancel_switch",
        target_user_id=None,
        target_username=None,
        details=f"系统管理员 {current_user.username} 取消切换用户",
        ip_address=None,
    )
    db.add(audit_log)
    db.commit()

    return current_user
```

#### 3. 修改批量创建学生API

```python
@router.post("/batch", response_model=BatchStudentResponse, status_code=status.HTTP_201_CREATED)
async def batch_create_students(
    data: BatchStudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """批量创建学生"""
    # 检查是否有切换用户
    if current_user.role == UserRole.SYSTEM_ADMIN:
        switched_user = db.query(User).filter(User.id == current_user.switched_user_id).first()
        if not switched_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要先选择要切换的目标用户"
            )
        # 使用切换用户的身份创建
        effective_user_id = current_user.switched_user_id
        effective_user = switched_user
    else:
        effective_user_id = current_user.id
        effective_user = current_user

    # 权限检查...
    # （后续创建逻辑）
```

### 3. 前端组件

#### `frontend/src/pages/UserManagement.tsx`

**新增功能：**

#### 1. 切换用户按钮（系统管理员专用）

```typescript
{user?.role === 'system_admin' && (
  <Button icon={<SwapOutlined />} onClick={handleSwitchUser}>
    切换用户
  </Button>
)}
```

#### 2. 切换用户弹窗

```typescript
<Modal
  title="切换用户身份"
  open={switchModalVisible}
  onCancel={() => {
    setSwitchModalVisible(false);
    setSwitchTargetUser(null);
  }}
  footer={[
    <Button key="cancel" onClick={handleCancelSwitch}>取消</Button>,
    <Button key="switch" type="primary" onClick={() => {
      if (switchTargetUser) {
        handleSwitchSubmit(switchTargetUser.id);
      }
    }} disabled={!switchTargetUser}>确认切换</Button>,
  ]}
  width={600}
>
  <Alert
    message="身份切换说明"
    description="..."
    type="info"
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
          const targetUser = users?.find((u: User) => u.id === value);
          setSwitchTargetUser(targetUser || null);
        }}
      >
        {users?.map((userItem: User) => (
          <Select.Option key={userItem.id} value={userItem.id}>
            {userItem.nickname || userItem.username}
          </Select.Option>
        ))}
      </Select>
    </Form.Item>

    <Alert
      message="权限说明"
      description={
        <div>
          <p>切换后将以用户 {...} (ID: {...}) 的身份进行操作</p>
          <p>当前用户：... (系统管理员)</p>
        </div>
      }
      type="info"
    />
</Form>
</Modal>
```

## 功能说明

### 1. 切换用户的工作流程

#### 正常流程（系统管理员）：

1. **选择要切换的用户**：
   - 点击"切换用户"按钮
   - 在弹窗中选择目标用户
   - 支持搜索用户名和昵称
   - 显示用户角色和用户名

2. **执行切换**：
   - 点击"确认切换"按钮
   - 系统管理员身份切换为目标用户
   - 记录切换日志到 `audit_logs` 表
   - 缓存切换状态到数据库
   - 前端显示成功提示

3. **批量创建/导入学生**：
   - 使用切换后的用户身份（学校ID、角色）
   - 批量创建或导入学生
   - 所有学生都分配到切换后的用户所属学校

4. **取消切换**：
   - 点击"取消"按钮
   - 恢复系统管理员身份
   - 清除切换状态
   - 记录取消切换日志

### 2. 权限控制

#### 系统管理员权限：
- ✅ 可以切换到任何非系统管理员用户
- ✅ 批量创建/导入时可以选择不同学校
- ✅ 切换后可以使用切换用户的角色和学校ID进行操作

#### 其他角色权限：
- ❌ 不能看到"切换用户"按钮（仅系统管理员可见）

#### 阻护措施：

```python
# 不能切换到系统管理员
if target_user.role == UserRole.SYSTEM_ADMIN:
    raise HTTPException(
        status_code=status.HTTP_403_FORBATCHEDEN,
        detail="不能切换到系统管理员"
    )

# 系统管理员才能切换用户
current_user: User = Depends(require_system_admin)
```

### 3. 审计日志

所有切换和取消操作都会记录到 `audit_logs` 表：

| 字段 | 说明 |
|------|------|
| `actor_id` | 执行切换操作的系统管理员ID |
| `target_user_id` | 切换到的用户ID |
| `action_type` | `switch_user` 或 `cancel_switch` |
| `details` | 详细的操作说明 |
| `ip_address` | 请求IP地址（可选）|
| `created_at` | 操作时间 |

### 4. 数据库表结构

#### users 表（新增字段）：

```sql
ALTER TABLE users
ADD COLUMN switched_user_id INT NULL,
ADD COLUMN switched_to_username VARCHAR(50) NULL,
ADD COLUMN switched_at DATETIME NULL;
```

#### audit_logs 表（新增表）：

```sql
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    actor_id INT NULL,
    target_user_id INT NULL,
    action_type VARCHAR(50) NOT NULL,
    details VARCHAR(500) NULL,
    ip_address VARCHAR(50) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_id) REFERENCES users(id),
    FOREIGN KEY (target_user_id) REFERENCES users(id)
);
```

## 使用场景

### 场景 1：系统管理员为不同学校批量创建学生

**操作步骤：**

1. 系统管理员 A 登录系统
2. 点击"切换用户"按钮
3. 在列表中选择学校管理员 B（属于学校 X）
4. 点击"确认切换"
5. 系统管理员现在以学校管理员 B 的身份操作
6. 点击"批量创建学生"
7. 在弹窗中选择学校 X
8. 批量创建学生，所有学生都分配到学校 X
9. 完成后点击"取消切换"恢复系统管理员 A 身份

**权限控制：**
- 切换前：系统管理员 A，可以访问所有学校
- 切换后：学校管理员 B，只能访问学校 X
- 创建的学生会使用学校管理员 B 的 school_id

### 场景 2：测试特定用户的功能

**操作步骤：**

1. 系统管理员切换到普通学生 S
2. 测试学生的页面权限和功能
3. 验证角色相关的UI和权限控制
4. 测试完成后取消切换，恢复系统管理员身份

### 场景 3：排查特定学生的问题

**操作步骤：**

1. 系统管理员切换到有问题的学生
2. 查看该学生的样本列表
3. 测试识别功能
4. 检查裁剪结果
5. 问题解决后恢复系统管理员身份

## 安全考虑

### 1. 审计追踪

- 所有切换操作都记录审计日志
- 包括操作时间、操作者、目标用户
- 用于追踪和问题排查

### 2. 权限保护

- 只有系统管理员可以切换用户
- 不能切换到其他系统管理员
- 切换状态存储在数据库中，可在任何会话中恢复

### 3. 会话管理

- 切换状态存储在用户模型中，而不是仅在会话中
- 支持跨会话保持（如果需要）
- 可以随时取消切换，恢复原身份

### 4. 前端状态同步

- 切换后刷新用户列表
- 更新 AuthContext 中的用户信息
- 显示当前身份和切换后的权限

### 5. 操作提示

- 切换成功/失败都有明确的消息提示
- 显示当前用户信息（切换后的用户）
- 明确说明切换的影响（如批量创建时的学校分配）

## 数据流

### 切换流程

```
系统管理员选择目标用户
    ↓
前端调用 GET /api/users/switch_user?target_user_id={id}
    ↓
后端验证权限（系统管理员 + 非系统管理员目标）
    ↓
后端更新 users 表中的 switched_* 字段
    ↓
后端插入审计日志记录
    ↓
返回目标用户信息
    ↓
前端更新用户上下文和UI
```

### 批量创建流程（使用切换后的用户）

```
系统管理员切换到学校管理员
    ↓
前端显示切换用户选择弹窗
    ↓
选择学校管理员后调用 GET /api/users/switch_user
    ↓
前端获取切换后的用户信息
    ↓
前端在批量创建表单中自动填充切换后用户的 school_id
    ↓
前端提交批量创建请求
    ↓
后端检查 users.switched_user_id
    ↓
后端使用切换后的用户权限创建学生
    ↓
所有学生都分配到切换后用户的学校
```

## 注意事项

1. **切换后需要刷新页面**：
   - 用户权限和列表会发生变化
   - 建议切换后重新加载用户列表

2. **跨设备支持**：
   - 当前实现切换状态存储在数据库中
   - 如果需要支持跨设备，需要添加设备ID

3. **并发处理**：
   - 系统管理员只能同时在一个会话中切换到一个用户
   - 切换操作应该是原子的

4. **数据库迁移**：
   - 需要运行数据库迁移添加新字段
   - 示例SQL在"数据库表结构"部分

5. **前端缓存刷新**：
   - 切换成功后清除相关的 React Query 缓存
   - 重新获取用户列表

## 测试建议

### 1. 测试正常切换流程

1. 登录系统管理员账号
2. 选择一个非系统管理员用户
3. 执行切换操作
4. 验证前端UI显示更新
5. 验证用户权限变更
6. 验证批量创建/导入功能

### 2. 测试取消切换

1. 执行用户切换
2. 执行一些操作（如批量创建）
3. 点击"取消切换"或"恢复身份"按钮
4. 验证恢复为原身份
5. 验证所有权限正确恢复

### 3. 测试权限保护

1. 尝试切换到系统管理员（应该被拒绝）
2. 学校管理员登录后验证看不到"切换用户"按钮
3. 切换到其他用户后验证不能切换到其他管理员

### 4. 测试批量创建

1. 切换到学校管理员
2. 批量创建学生
3. 验证所有学生都分配到正确的学校
4. 取消切换后验证批量创建功能不可用

## 扩展性

### 未来改进

1. **切换历史**：
   - 添加切换历史记录
   - 支持快速切换到之前切换过的用户
   - 显示最近切换的用户

2. **自动恢复**：
   - 切换超时后自动恢复
   - 或者提供自动恢复的选项

3. **批量操作**：
   - 支持批量切换用户
   - 为每个用户执行特定操作

4. **身份标识**：
   - 在界面上明确显示当前操作身份
   - 使用不同的颜色或图标标识

## 故障排查

### 问题 1：切换后权限未更新

**解决方案**：
1. 检查 AuthContext 是否正确刷新
2. 清除 React Query 缓存
3. 重新获取用户信息

### 问题 2：批量创建时权限错误

**解决方案：**
1. 确认切换状态已更新到数据库
2. 验证后端使用的是 `switched_user_id`
3. 检查批量创建API的权限检查逻辑

### 问题 3：切换后无法创建学生

**解决方案**：
1. 确认目标用户的 school_id
2. 检查批量创建时使用的是切换后的用户ID
3. 检查批量创建中的学校ID过滤逻辑

## 总结

**主要改进**：
1. ✅ 新增用户表字段存储切换状态
2. ✅ 新增审计日志表记录切换操作
3. ✅ 新增切换用户API端点（系统管理员专用）
4. ✅ 新增取消切换API端点（系统管理员专用）
5. ✅ 前端添加切换用户按钮和弹窗
6. ✅ 批量创建API支持切换后的用户身份

**用户体验提升**：
1. ✅ 系统管理员可以快速切换身份进行批量操作
2. ✅ 支持为不同学校批量创建学生
3. ✅ 清晰的权限说明和状态提示
4. ✅ 完整的操作审计追踪
5. ✅ 随时可以取消切换，恢复原身份

所有功能已实现完成！系统管理员现在可以快速切换到其他用户身份来执行批量操作，同时保持了严格的权限控制和审计记录。
