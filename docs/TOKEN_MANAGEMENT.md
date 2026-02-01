# Token 管理功能文档

## 概述

Token 管理功能允许用户创建和管理 API Token，用于外部应用集成到字迹识别系统。系统提供：

- ✅ **Token 创建**：创建带有特定权限的 API Token
- ✅ **权限控制**：细粒度的权限配置
- ✅ **Token 列表**：查看所有已创建的 Token 及其使用情况
- ✅ **Token 撤销**：撤销（停用）Token 而不删除
- ✅ **Token 删除**：永久删除 Token
- ✅ **安全显示**：Token 只在创建时显示一次
- ✅ **API 测试**：快速测试 Token 功能的在线工具

---

## 功能特性

### 1. Token 创建

**位置**: `/tokens`

**功能**:
- 创建新的 API Token 用于外部应用集成
- 配置 Token 名称、应用信息
- 选择作用域（read/write/admin）
- 细粒度权限配置

**权限规则**:

| 用户角色 | 可创建的作用域 |
|---------|--------------|
| student | read |
| teacher | read, write |
| school_admin | read, write, admin |
| system_admin | read, write, admin |

**权限说明**:

| 权限 | 说明 | 依赖作用域 |
|------|------|-----------|
| 读取样本 | 可以查看和列出样本 | read, write, admin |
| 写入样本 | 可以上传样本 | write, admin |
| 识别 | 可以执行字迹识别 | write, admin |
| 读取用户 | 可以查看用户信息 | read, write, admin |
| 训练管理 | 可以管理模型训练 | admin |

**使用场景**:

- **只读 Token**: 供外部系统查看样本和用户信息
- **读写 Token**: 供教学系统集成，可上传和识别
- **管理员 Token**: 供系统集成完全功能

### 2. Token 列表

**功能**:
- 查看所有已创建的 Token
- 显示 Token 状态（活跃/已撤销）
- 查看使用次数和最后使用时间
- 查看权限配置
- 支持分页和排序

**显示信息**:
- Token 名称和应用信息
- 作用域和权限标签
- 活跃状态
- 使用统计
- 创建和最后使用时间

### 3. Token 撤销

**功能**:
- 撤销（停用）Token 而不删除
- 被撤销的 Token 无法再使用 API
- 保留 Token 记录以便查看

**适用场景**:
- 临时禁用某个应用的访问权限
- 怀疑 Token 泄露时快速响应
- 不想删除 Token 记录但需要禁用

### 4. Token 删除

**功能**:
- 永久删除 Token 记录
- 删除后无法恢复
- 需要确认操作

**适用场景**:
- 应用不再使用
- Token 已过期或不再需要
- 清理无效的 Token

### 5. API 测试

**位置**: `/api-test`

**功能**:
- 在线测试 Token API 的各项功能
- 选择常用 API 端点进行测试
- 查看 API 响应和请求详情
- 复制 cURL 命令

**支持的测试端点**:
- 获取当前用户信息
- 获取 API 配置
- 获取 API 信息
- 验证 Token
- 列出 Token
- 列出样本
- 字迹识别
- 上传样本
- 获取用户信息
- 获取训练记录

---

## 安全特性

### 1. Token 只显示一次

Token 在创建成功后通过 Modal 显示，包含：

- ⚠️ **红色警告提示**: 明确告知 Token 只显示一次
- 🔐 **默认掩码显示**: 只显示前 8 位和后 4 位
- 👁️ **显示/隐藏切换**: 可以查看完整 Token
- 📋 **一键复制**: 方便保存到安全位置
- 📝 **使用说明**: 提供 Authorization Header 示例

### 2. 权限验证

**后端验证**:
- 每次请求都验证 Token 有效性
- 检查 Token 是否被撤销
- 验证 Token 是否有请求的权限
- 记录 Token 使用统计

**作用域限制**:
- `read`: 只能访问读取端点
- `write`: 可以访问读取和写入端点
- `admin`: 可以访问所有端点

### 3. 角色权限

**Token 创建权限**:
- 学生只能创建 `read` Token
- 教师可以创建 `read` 或 `write` Token
- 管理员可以创建任意作用域的 Token

**Token 管理权限**:
- 学生只能管理自己的 Token
- 学校管理员可以管理本校的所有 Token
- 系统管理员可以管理所有 Token

---

## API 端点

### Token 管理

| 方法 | 端点 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/tokens/create` | 创建 Token | 是 |
| GET | `/api/tokens/list` | 列出 Token | 是 |
| GET | `/api/tokens/{id}` | 获取 Token 详情 | 是 |
| POST | `/api/tokens/{id}/revoke` | 撤销 Token | 是 |
| DELETE | `/api/tokens/{id}` | 删除 Token | 是 |

### Token API

| 方法 | 端点 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/tokens/create` | 创建外部访问令牌 | 否 |
| POST | `/api/v1/tokens/verify` | 验证令牌 | 否 |
| GET | `/api/v1/tokens/me` | 获取当前用户 | Bearer Token |
| POST | `/api/v1/tokens/revoke` | 撤销令牌 | Bearer Token |
| GET | `/api/v1/tokens/config` | 获取配置 | Bearer Token |
| GET | `/api/v1/tokens/info` | 获取信息 | 否 |

---

## 使用示例

### Python 示例

```python
import requests

# 创建 Token
def create_token(username, password):
    response = requests.post(
        'http://localhost:8000/api/tokens/create',
        json={
            'username': username,
            'password': password,
            'app_name': 'MyApp',
            'scope': 'write'
        }
    )
    return response.json()

# 使用 Token
def recognize_image(token, image_path):
    with open(image_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/recognition',
            headers={'Authorization': f'Bearer {token}'},
            files={'file': f}
        )
    return response.json()

# 示例
token_response = create_token('teacher1', 'password123')
token = token_response['access_token']
print(f'Token: {token}')

# 使用 Token 进行识别
# result = recognize_image(token, 'test_image.jpg')
```

### JavaScript 示例

```javascript
const axios = require('axios');

// 创建 Token
async function createToken(username, password) {
    const response = await axios.post('http://localhost:8000/api/tokens/create', {
        username,
        password,
        app_name: 'MyApp',
        scope: 'write'
    });
    return response.data;
}

// 使用 Token
async function recognizeImage(token, imagePath) {
    const FormData = require('form-data');
    const fs = require('fs');
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));

    const response = await axios.post(
        'http://localhost:8000/api/recognition',
        form,
        {
            headers: {
                ...form.getHeaders(),
                Authorization: `Bearer ${token}`
            }
        }
    );
    return response.data;
}

// 示例
(async () => {
    const { access_token } = await createToken('teacher1', 'password123');
    console.log(`Token: ${access_token}`);

    // 使用 Token 进行识别
    // const result = await recognizeImage(access_token, 'test_image.jpg');
})();
```

### cURL 示例

```bash
# 创建 Token
curl -X POST http://localhost:8000/api/tokens/create \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher1",
    "password": "password123",
    "app_name": "MyApp",
    "scope": "write"
  }'

# 使用 Token 获取当前用户
curl -X GET http://localhost:8000/api/v1/tokens/me \
  -H "Authorization: Bearer hwtk_xxx..."

# 使用 Token 进行识别
curl -X POST http://localhost:8000/api/recognition \
  -H "Authorization: Bearer hwtk_xxx..." \
  -F "file=@test_image.jpg"
```

---

## 前端页面

### Token 管理页面 (`/tokens`)

**功能组件**:
1. **Token 列表表格**
   - 显示所有 Token
   - 分页支持
   - 排序和过滤
   - 操作按钮（撤销、删除）

2. **创建 Token Modal**
   - Token 名称输入
   - 应用名称和版本
   - 作用域选择
   - 权限复选框
   - 安全提示

3. **Token 创建成功 Modal**
   - Token 显示（默认掩码）
   - 显示/隐藏切换
   - 复制按钮
   - 使用说明
   - 重要警告提示

### API 测试页面 (`/api-test`)

**功能组件**:
1. **API 请求配置**
   - Token 输入
   - 端点选择下拉框
   - 请求体编辑器
   - 发送按钮
   - 复制 cURL 按钮

2. **API 响应显示**
   - 状态码和响应时间
   - 响应数据格式化显示
   - 响应头详情（可折叠）

3. **API 使用说明**
   - 获取 Token 步骤
   - 使用 Token 格式
   - Token 权限说明
   - 错误处理指南

---

## 数据库表结构

### api_tokens 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| token | VARCHAR(255) | API Token（唯一） |
| name | VARCHAR(100) | Token 名称 |
| app_name | VARCHAR(100) | 应用名称 |
| app_version | VARCHAR(50) | 应用版本 |
| scope | VARCHAR(50) | 作用域（read/write/admin） |
| can_read_samples | BOOLEAN | 读取样本权限 |
| can_write_samples | BOOLEAN | 写入样本权限 |
| can_recognize | BOOLEAN | 识别权限 |
| can_read_users | BOOLEAN | 读取用户权限 |
| can_manage_training | BOOLEAN | 训练管理权限 |
| user_id | INT | 所属用户ID |
| school_id | INT | 所属学校ID |
| is_active | BOOLEAN | 是否活跃 |
| is_revoked | BOOLEAN | 是否被撤销 |
| created_at | DATETIME | 创建时间 |
| expires_at | DATETIME | 过期时间 |
| last_used_at | DATETIME | 最后使用时间 |
| revoked_at | DATETIME | 撤销时间 |
| usage_count | INT | 使用次数 |
| last_ip | VARCHAR(50) | 最后使用IP |

---

## 常见问题

### Q: Token 泄露了怎么办？

**A**: 立即撤销 Token：
1. 进入 Token 管理页面
2. 找到泄露的 Token
3. 点击"撤销"按钮
4. 创建新的 Token 替换

### Q: Token 过期了怎么办？

**A**: Token 默认有效期为 1 年。过期后：
- Token 将自动失效
- 需要创建新的 Token
- 旧的 Token 记录保留，但无法使用

### Q: 如何查看 Token 的使用情况？

**A**: 在 Token 列表中可以看到：
- 使用次数：API 调用总数
- 最后使用时间：最后一次调用的时间
- 活跃状态：Token 是否可用

### Q: 不同角色的用户能创建什么 Token？

**A**:
- **学生**: 只能创建 `read` Token
- **教师**: 可以创建 `read` 或 `write` Token
- **学校管理员**: 可以创建 `read`、`write` 或 `admin` Token
- **系统管理员**: 可以创建任意作用域的 Token

### Q: Token 创建后可以重新查看吗？

**A**: 不可以。Token 只在创建时显示一次，之后无法查看完整 Token。如果忘记了 Token，需要：
1. 撤销旧 Token
2. 创建新 Token

### Q: 如何撤销 Token 而不删除？

**A**: 点击 Token 列表中的"撤销"按钮即可。撤销后：
- Token 无法使用
- 记录保留在列表中
- 可以查看历史信息

### Q: Token 可以同时用于多个应用吗？

**A**: 可以。一个 Token 可以被多个应用同时使用，但建议：
- 为不同应用创建不同的 Token
- 使用描述性的 Token 名称
- 便于追踪和管理

---

## 最佳实践

### 1. Token 安全

- ✅ 创建后立即保存到安全的位置
- ✅ 使用环境变量或密钥管理服务存储 Token
- ✅ 不要在代码中硬编码 Token
- ✅ 定期轮换 Token
- ✅ 使用最小权限原则

### 2. 权限配置

- ✅ 只授予必要的权限
- ✅ 为不同环境使用不同 Token
- ✅ 为测试和生产分别创建 Token
- ✅ 定期审查 Token 权限

### 3. Token 管理

- ✅ 使用描述性的 Token 名称
- ✅ 记录 Token 的用途和应用
- ✅ 定期清理不用的 Token
- ✅ 监控 Token 使用情况

### 4. 错误处理

- ✅ 妥善处理 401 错误（Token 无效）
- ✅ 妥善处理 403 错误（权限不足）
- ✅ 实现 Token 自动刷新机制（如果适用）
- ✅ 记录 API 调用错误日志

---

## 更新日志

### v1.0.0 (2026-01-31)

- ✅ 实现 Token 创建功能
- ✅ 实现权限控制和作用域
- ✅ 实现 Token 列表查看
- ✅ 实现 Token 撤销和删除
- ✅ 实现 Token 安全显示（只显示一次）
- ✅ 实现 API 测试页面
- ✅ 添加数据库迁移
- ✅ 更新文档

---

## 相关文档

- [Token API 快速入门](./TOKEN_API_QUICKSTART.md)
- [Token API 完整文档](./TOKEN_API.md)
- [项目 README](../README.md)
- [开发指南](./DEVELOPMENT.md)
