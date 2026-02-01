# Token API 用户和学校管理文档

## 概述

Token API 的用户和学校管理功能允许外部应用通过 Token 来创建、编辑、删除用户和管理学校，具有完整的权限控制系统。

---

## API 端点列表

### 用户管理

| 方法 | 端点 | 说明 | 权限要求 |
|------|------|------|-----------|
| POST | `/api/v1/users` | 创建用户 | `manage_users` 或 scope `write`/`admin` |
| GET | `/api/v1/users` | 列出用户 | `read_users` 或 scope `read`+ |
| GET | `/api/v1/users/{user_id}` | 获取用户详情 | `read_users` 或 scope `read`+ |
| PUT | `/api/v1/users/{user_id}` | 更新用户信息 | `manage_users` 或 scope `write`/`admin` |
| POST | `/api/v1/users/{user_id}/password` | 设置用户密码 | `manage_users` 或 scope `write`/`admin` |
| DELETE | `/api/v1/users/{user_id}` | 删除用户 | `manage_users` 或 scope `write`/`admin` |

### 学校管理

| 方法 | 端点 | 说明 | 权限要求 |
|------|------|------|-----------|
| POST | `/api/v1/schools` | 创建学校 | `manage_training` 或 scope `admin` |
| GET | `/api/v1/schools` | 列出所有学校 | `read_users` 或 scope `read`+ |
| GET | `/api/v1/schools/{school_id}` | 获取学校详情 | `read_users` 或 scope `read`+ |
| PUT | `/api/v1/schools/{school_id}` | 更新学校信息 | `manage_training` 或 scope `admin` |
| DELETE | `/api/v1/schools/{school_id}` | 删除学校 | `manage_training` 或 scope `admin` |

---

## 权限系统

### Token 权限

Token 支持以下权限，需要在创建 Token 时配置：

| 权限 | 说明 | 建议作用域 |
|------|------|-----------|
| `read_users` | 可以查看用户和学校信息 | `read`, `write`, `admin` |
| `manage_users` | 可以创建、编辑、删除用户，设置密码 | `write`, `admin` |
| `manage_training` | 可以管理学校信息 | `admin` |

### 用户角色权限

| 用户角色 | 可执行的操作 |
|---------|-----------|
| **student** | - 查看自己的信息<br>- 修改自己的昵称<br>- 设置自己的密码 |
| **teacher** | - 创建学生<br>- 编辑学生信息<br>- 设置学生密码<br>- 删除学生<br>- 查看本校所有学生 |
| **school_admin** | - 创建学生和教师<br>- 编辑本校所有用户信息<br>- 设置本校用户密码<br>- 删除学生和教师<br>- 查看本校所有用户 |
| **system_admin** | - 创建任意角色用户<br>- 编辑任意用户信息<br>- 设置任意用户密码<br>- 删除任意用户<br>- 查看所有用户<br>- 管理学校（创建/编辑/删除） |

### 权限验证规则

**创建用户**：
- ✅ 学生可以创建学生
- ✅ 教师可以创建本校学生
- ✅ 学校管理员可以创建本校学生和教师
- ✅ 系统管理员可以创建任意角色用户

**编辑用户**：
- ✅ 用户可以编辑自己的信息（不能修改角色和学校）
- ✅ 教师可以编辑本校学生
- ✅ 学校管理员可以编辑本校任何用户
- ✅ 系统管理员可以编辑任何用户

**设置密码**：
- ✅ 用户可以设置自己的密码
- ✅ 教师可以设置本校学生密码
- ✅ 学校管理员可以设置本校任何用户密码
- ✅ 系统管理员可以设置任何用户密码

**删除用户**：
- ❌ 不能删除自己的账户
- ✅ 教师可以删除本校学生
- ✅ 学校管理员可以删除本校学生和教师
- ✅ 系统管理员可以删除任何用户

**管理学校**：
- ❌ 学生/教师/学校管理员不能管理学校
- ✅ 只有系统管理员可以创建/编辑/删除学校

---

## API 端点详解

### 1. 创建用户

**端点**: `POST /api/v1/users`

**请求头**: `Authorization: Bearer <token>`

**请求体**:
```json
{
  "username": "student1",
  "password": "password123",
  "nickname": "张三",
  "role": "student",
  "school_id": 1
}
```

**参数说明**:
- `username`: 用户名（必填，唯一）
- `password`: 密码（必填）
- `nickname`: 昵称/姓名（可选）
- `role`: 角色（必填）
  - `student`: 学生
  - `teacher`: 教师
  - `school_admin`: 学校管理员
  - `system_admin`: 系统管理员
- `school_id`: 学校 ID（可选，默认使用 Token 用户的学校）

**响应**:
```json
{
  "id": 10,
  "username": "student1",
  "nickname": "张三",
  "role": "student",
  "school_id": 1,
  "created_at": "2026-01-31T10:00:00Z"
}
```

**错误响应**:
- `400 Bad Request`: 用户名已存在或角色无效
- `403 Forbidden`: 权限不足
- `404 Not Found`: 学校不存在

---

### 2. 更新用户信息

**端点**: `PUT /api/v1/users/{user_id}`

**请求头**: `Authorization: Bearer <token>`

**请求体**:
```json
{
  "nickname": "张三（更新）",
  "role": "student",
  "school_id": 1
}
```

**参数说明**:
- `nickname`: 昵称/姓名（可选）
- `role`: 角色（可选）
- `school_id`: 学校 ID（可选）

**响应**:
```json
{
  "id": 10,
  "username": "student1",
  "nickname": "张三（更新）",
  "role": "student",
  "school_id": 1,
  "created_at": "2026-01-31T10:00:00Z"
}
```

---

### 3. 设置用户密码

**端点**: `POST /api/v1/users/{user_id}/password`

**请求头**: `Authorization: Bearer <token>`

**请求体**:
```json
{
  "password": "newpassword123"
}
```

**参数说明**:
- `password`: 新密码（必填）

**响应**:
```json
{
  "message": "Password updated successfully"
}
```

---

### 4. 删除用户

**端点**: `DELETE /api/v1/users/{user_id}`

**请求头**: `Authorization: Bearer <token>`

**响应**: `204 No Content`

**说明**:
- 删除用户会级联删除其样本、特征和 Token
- 不能删除自己的账户
- 不能删除管理员用户（根据角色权限）

**错误响应**:
- `400 Bad Request`: 尝试删除自己
- `403 Forbidden`: 权限不足或尝试删除管理员用户
- `404 Not Found`: 用户不存在

---

### 5. 获取用户详情

**端点**: `GET /api/v1/users/{user_id}`

**请求头**: `Authorization: Bearer <token>`

**查询参数**:
- `user_id`: 用户 ID（路径参数）

**响应**:
```json
{
  "id": 10,
  "username": "student1",
  "nickname": "张三",
  "role": "student",
  "school_id": 1,
  "created_at": "2026-01-31T10:00:00Z"
}
```

---

### 6. 列出用户

**端点**: `GET /api/v1/users`

**请求头**: `Authorization: Bearer <token>`

**查询参数**:
- `school_id`: 按学校 ID 过滤（可选）
- `role`: 按角色过滤（可选）

**响应**:
```json
[
  {
    "id": 10,
    "username": "student1",
    "nickname": "张三",
    "role": "student",
    "school_id": 1,
    "created_at": "2026-01-31T10:00:00Z"
  }
]
```

**权限说明**:
- 学生只能看到自己
- 教师只能看到本校学生
- 学校管理员只能看到本校所有用户
- 系统管理员可以看到所有用户

---

### 7. 创建学校

**端点**: `POST /api/v1/schools`

**请求头**: `Authorization: Bearer <token>`

**请求体**:
```json
{
  "name": "北京大学"
}
```

**参数说明**:
- `name`: 学校名称（必填，唯一）

**响应**:
```json
{
  "id": 5,
  "name": "北京大学",
  "created_at": "2026-01-31T10:00:00Z",
  "user_count": 0
}
```

**错误响应**:
- `400 Bad Request`: 学校名称已存在
- `403 Forbidden`: 权限不足（非系统管理员）

---

### 8. 更新学校信息

**端点**: `PUT /api/v1/schools/{school_id}`

**请求头**: `Authorization: Bearer <token>`

**请求体**:
```json
{
  "name": "北京大学（更新）"
}
```

**参数说明**:
- `name`: 学校名称（必填）

**响应**:
```json
{
  "id": 5,
  "name": "北京大学（更新）",
  "created_at": "2026-01-31T10:00:00Z",
  "user_count": 50
}
```

**错误响应**:
- `400 Bad Request`: 学校名称已存在
- `403 Forbidden`: 权限不足（非系统管理员）
- `404 Not Found`: 学校不存在

---

### 9. 删除学校

**端点**: `DELETE /api/v1/schools/{school_id}`

**请求头**: `Authorization: Bearer <token>`

**响应**: `204 No Content`

**说明**:
- 不能删除有用户的学校
- 需要先删除所有用户

**错误响应**:
- `400 Bad Request`: 学校下有用户，无法删除
- `403 Forbidden`: 权限不足（非系统管理员）
- `404 Not Found`: 学校不存在

---

### 10. 获取学校详情

**端点**: `GET /api/v1/schools/{school_id}`

**请求头**: `Authorization: Bearer <token>`

**查询参数**:
- `school_id`: 学校 ID（路径参数）

**响应**:
```json
{
  "id": 1,
  "name": "清华大学",
  "created_at": "2026-01-01T00:00:00Z",
  "user_count": 50
}
```

---

### 11. 列出所有学校

**端点**: `GET /api/v1/schools`

**请求头**: `Authorization: Bearer <token>`

**响应**:
```json
[
  {
    "id": 1,
    "name": "清华大学",
    "created_at": "2026-01-01T00:00:00Z",
    "user_count": 50
  },
  {
    "id": 2,
    "name": "北京大学",
    "created_at": "2026-01-01T00:00:00Z",
    "user_count": 45
  }
]
```

---

## 使用示例

### Python 示例

```python
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "hwtk_xxx..."  # 替换为实际的 Token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. 创建用户
def create_user(username, password, nickname, role, school_id=None):
    response = requests.post(
        f"{BASE_URL}/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": password,
            "nickname": nickname,
            "role": role,
            "school_id": school_id
        }
    )
    return response.json()

# 2. 更新用户
def update_user(user_id, **kwargs):
    response = requests.put(
        f"{BASE_URL}/api/v1/users/{user_id}",
        headers=headers,
        json=kwargs
    )
    return response.json()

# 3. 设置密码
def set_password(user_id, new_password):
    response = requests.post(
        f"{BASE_URL}/api/v1/users/{user_id}/password",
        headers=headers,
        json={"password": new_password}
    )
    return response.json()

# 4. 删除用户
def delete_user(user_id):
    response = requests.delete(
        f"{BASE_URL}/api/v1/users/{user_id}",
        headers=headers
    )
    return response.status_code == 204

# 5. 创建学校
def create_school(name):
    response = requests.post(
        f"{BASE_URL}/api/v1/schools",
        headers=headers,
        json={"name": name}
    )
    return response.json()

# 示例使用
if __name__ == "__main__":
    # 创建学生
    student = create_user(
        username="student100",
        password="password123",
        nickname="李四",
        role="student",
        school_id=1
    )
    print(f"Created student: {json.dumps(student, indent=2)}")

    # 更新学生信息
    updated = update_user(
        student["id"],
        nickname="李四（更新）"
    )
    print(f"Updated student: {json.dumps(updated, indent=2)}")

    # 设置密码
    result = set_password(student["id"], "newpassword456")
    print(f"Password set: {json.dumps(result, indent=2)}")

    # 删除学生
    if delete_user(student["id"]):
        print("Student deleted successfully")

    # 创建学校（需要 system admin 角色）
    # school = create_school("浙江大学")
    # print(f"Created school: {json.dumps(school, indent=2)}")
```

### JavaScript 示例

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';
const TOKEN = 'hwtk_xxx...'; // 替换为实际的 Token

const api = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Content-Type': 'application/json'
    }
});

// 1. 创建用户
async function createUser(username, password, nickname, role, schoolId) {
    const response = await api.post('/api/v1/users', {
        username,
        password,
        nickname,
        role,
        school_id: schoolId
    });
    return response.data;
}

// 2. 更新用户
async function updateUser(userId, data) {
    const response = await api.put(`/api/v1/users/${userId}`, data);
    return response.data;
}

// 3. 设置密码
async function setPassword(userId, newPassword) {
    const response = await api.post(`/api/v1/users/${userId}/password`, {
        password: newPassword
    });
    return response.data;
}

// 4. 删除用户
async function deleteUser(userId) {
    const response = await api.delete(`/api/v1/users/${userId}`);
    return response.status === 204;
}

// 5. 创建学校
async function createSchool(name) {
    const response = await api.post('/api/v1/schools', { name });
    return response.data;
}

// 示例使用
(async () => {
    try {
        // 创建学生
        const student = await createUser(
            'student100',
            'password123',
            '李四',
            'student',
            1
        );
        console.log('Created student:', JSON.stringify(student, null, 2));

        // 更新学生信息
        const updated = await updateUser(student.id, {
            nickname: '李四（更新）'
        });
        console.log('Updated student:', JSON.stringify(updated, null, 2));

        // 设置密码
        const result = await setPassword(student.id, 'newpassword456');
        console.log('Password set:', JSON.stringify(result, null, 2));

        // 删除学生
        const deleted = await deleteUser(student.id);
        console.log('Student deleted:', deleted);

        // 创建学校（需要 system admin 角色）
        // const school = await createSchool('浙江大学');
        // console.log('Created school:', JSON.stringify(school, null, 2));

    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
})();
```

### cURL 示例

```bash
# 设置变量
TOKEN="hwtk_xxx..."  # 替换为实际的 Token
BASE_URL="http://localhost:8000"

# 1. 创建用户
curl -X POST ${BASE_URL}/api/v1/users \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student100",
    "password": "password123",
    "nickname": "李四",
    "role": "student",
    "school_id": 1
  }'

# 2. 更新用户
curl -X PUT ${BASE_URL}/api/v1/users/10 \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "nickname": "李四（更新）"
  }'

# 3. 设置密码
curl -X POST ${BASE_URL}/api/v1/users/10/password \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "newpassword456"
  }'

# 4. 删除用户
curl -X DELETE ${BASE_URL}/api/v1/users/10 \
  -H "Authorization: Bearer ${TOKEN}"

# 5. 获取用户列表
curl -X GET "${BASE_URL}/api/v1/users?role=student&school_id=1" \
  -H "Authorization: Bearer ${TOKEN}"

# 6. 创建学校
curl -X POST ${BASE_URL}/api/v1/schools \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "浙江大学"
  }'

# 7. 列出学校
curl -X GET ${BASE_URL}/api/v1/schools \
  -H "Authorization: Bearer ${TOKEN}"

# 8. 删除学校
curl -X DELETE ${BASE_URL}/api/v1/schools/5 \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 错误处理

### 常见错误代码

| 状态码 | 说明 | 解决方法 |
|--------|------|---------|
| 400 Bad Request | 请求参数错误 | 检查请求体格式和参数 |
| 401 Unauthorized | Token 无效或已过期 | 重新获取 Token |
| 403 Forbidden | 权限不足 | 检查 Token 权限和用户角色 |
| 404 Not Found | 资源不存在 | 确认用户/学校 ID 正确 |
| 500 Internal Server Error | 服务器错误 | 联系系统管理员 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

---

## 安全最佳实践

### 1. Token 安全

- ✅ 使用 HTTPS 传输 Token
- ✅ 不要在代码中硬编码 Token
- ✅ 定期轮换 Token
- ✅ 使用最小权限原则
- ✅ 及时撤销不用的 Token

### 2. 用户管理

- ✅ 验证用户名格式和强度
- ✅ 使用强密码策略
- ✅ 记录用户创建/修改/删除操作
- ✅ 实施审计日志

### 3. 权限控制

- ✅ 遵循最小权限原则
- ✅ 定期审查用户权限
- ✅ 为不同应用创建不同 Token
- ✅ 监控 Token 使用情况

---

## 常见问题

### Q: 如何为外部应用创建 Token？

**A**: 
1. 登录系统
2. 进入 Token 管理页面
3. 点击"创建 Token"
4. 配置权限（`manage_users` 用于用户管理）
5. 保存 Token（只显示一次）

### Q: Token 权限如何工作？

**A**: Token 创建时配置权限，每次 API 请求都会验证：
- `read_users`: 可以读取用户和学校信息
- `manage_users`: 可以创建、编辑、删除用户和设置密码
- `manage_training`: 可以管理学校信息

### Q: 学生可以创建用户吗？

**A**: 不可以。学生只能查看和编辑自己的信息。

### Q: 教师可以创建什么角色的用户？

**A**: 教师只能创建学生（`student` 角色），且必须是本校的。

### Q: 如何删除有用户的学校？

**A**: 
1. 先删除学校下的所有用户
2. 然后才能删除学校
3. 或联系系统管理员协助

### Q: 删除用户会发生什么？

**A**: 删除用户会级联删除：
- 用户的样本
- 用户的特征数据
- 用户的 Token
- 用户的识别日志

---

## 更新日志

### v1.0.0 (2026-01-31)

- ✅ 实现用户创建 API
- ✅ 实现用户信息更新 API
- ✅ 实现用户密码设置 API
- ✅ 实现用户删除 API（权限验证）
- ✅ 实现学校创建 API
- ✅ 实现学校更新 API
- ✅ 实现学校删除 API
- ✅ 实现完整的权限验证系统
- ✅ 添加详细的 API 文档

---

## 相关文档

- [Token API 快速入门](./TOKEN_API_QUICKSTART.md)
- [Token API 完整文档](./TOKEN_API.md)
- [Token 管理功能](./TOKEN_MANAGEMENT.md)
- [项目 README](../README.md)
