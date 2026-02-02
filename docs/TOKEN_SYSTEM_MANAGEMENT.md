# Token系统管理权限文档

## 概述

本文档描述了API Token的系统管理权限功能，包括重载系统配置和配额限制管理等功能。

## 功能特性

### 1. 系统管理权限（manage_system）

API Token新增了`can_manage_system`权限字段，允许通过token访问系统级别的管理功能。

#### 支持的功能

- **系统配置重载** - 重新加载系统配置，无需重启服务
- **配额限制管理** - 设置和管理用户/学校的请求配额
- **系统配置查询** - 查看当前系统配置信息

### 2. 权限等级

Token权限分为以下几类：

| 权限名称 | 说明 | 适用范围 |
|---------|------|---------|
| `read_samples` | 读取样本信息 | 查看样本列表和详情 |
| `write_samples` | 上传样本 | 创建新的样本 |
| `recognize` | 字迹识别 | 执行识别请求 |
| `read_users` | 读取用户信息 | 查看用户列表和详情 |
| `manage_users` | 管理用户 | 创建、修改、删除用户 |
| `manage_schools` | 管理学校 | 创建、修改、删除学校 |
| `manage_training` | 管理训练 | 触发和管理模型训练 |
| **`manage_system`** | **系统管理** | **重载配置、管理配额** |

### 3. Token作用域（Scope）

Token可以通过`scope`参数设置权限级别：

#### 作用域等级

- **`read`** - 只读权限
  - 自动包含: `read_samples`, `read_users`

- **`write`** - 写入权限
  - 自动包含: `read_samples`, `write_samples`, `recognize`, `read_users`

- **`admin`** - 管理员权限
  - 自动包含: **所有权限**，包括 `manage_system`

#### 自定义权限

除了使用scope，还可以在创建token时指定具体的权限列表：

```json
{
  "name": "系统管理Token",
  "scope": "admin",
  "permissions": ["manage_system", "manage_users"],
  "expiration_type": "30d"
}
```

## API端点

### 1. 创建Token（包含系统管理权限）

**端点**: `POST /api/tokens/create`

**请求示例**:

```json
{
  "name": "系统管理Token",
  "app_name": "系统集成",
  "app_version": "1.0.0",
  "scope": "admin",
  "expiration_type": "30d"
}
```

**响应示例**:

```json
{
  "id": 1,
  "name": "系统管理Token",
  "token": "hwtk_abc123...",
  "scope": "admin",
  "permissions": {
    "read_samples": true,
    "write_samples": true,
    "recognize": true,
    "read_users": true,
    "manage_users": true,
    "manage_schools": true,
    "manage_training": true,
    "manage_system": true
  },
  "created_at": "2026-02-02T00:00:00Z",
  "expires_at": "2026-03-04T00:00:00Z",
  "message": "Token created successfully. Save this token now - it will not be shown again!"
}
```

### 2. 系统配置重载

**端点**: `POST /api/system/reload`

**权限要求**:
- JWT Token: 需要 `system_admin` 角色
- API Token: 需要 `manage_system` 权限

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/system/reload \
  -H "Authorization: Bearer hwtk_abc123..."
```

**响应示例**:

```json
{
  "message": "系统配置已重新加载",
  "reloaded": true
}
```

### 3. 获取系统配置

**端点**: `GET /api/system/config`

**权限要求**:
- JWT Token: 需要 `system_admin` 角色
- API Token: 需要 `manage_system` 权限

**请求示例**:

```bash
curl -X GET http://localhost:8000/api/system/config \
  -H "Authorization: Bearer hwtk_abc123..."
```

**响应示例**:

```json
{
  "database_url": "mysql+pymysql://***",
  "inference_service": "localhost:50051",
  "redis": "localhost:6379",
  "upload_dir": "./uploads",
  "samples_dir": "./uploads/samples",
  "models_dir": "./models",
  "max_upload_size": 10485760,
  "max_upload_size_mb": 10,
  "cors_origins": ["http://localhost:3000", "http://localhost:5173"]
}
```

### 4. 设置用户配额

**端点**: `POST /api/v1/tokens/quota/set`

**权限要求**:
- JWT Token: 需要 `school_admin` 或 `system_admin` 角色
- API Token:
  - 用户级配额: 需要 `manage_users` 或 `manage_system` 权限
  - 学校级配额: 需要 `manage_system` 权限

**请求示例（设置用户配额）**:

```json
{
  "quota_type": "user",
  "user_id": 5,
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "description": "标准学生配额"
}
```

**请求示例（设置学校配额 - 需要manage_system权限）**:

```json
{
  "quota_type": "school",
  "school_id": 1,
  "minute_limit": 50,
  "hour_limit": 500,
  "day_limit": 5000,
  "month_limit": 50000,
  "total_limit": 0,
  "description": "学校A配额"
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "Quota updated successfully",
  "quota_id": 1
}
```

### 5. 批量设置配额

**端点**: `POST /api/v1/tokens/quota/batch-set`

**权限要求**: 与单个设置相同

**请求示例**:

```json
{
  "user_ids": [1, 2, 3, 4, 5],
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "description": "批量学生配额更新"
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "Batch quota update completed",
  "updated_count": 5
}
```

### 6. 重置配额使用计数

**端点**: `POST /api/v1/tokens/quota/reset`

**权限要求**:
- JWT Token: 需要 `school_admin` 或 `system_admin` 角色
- API Token: 需要 `manage_system` 权限（或根据拥有权限）

**请求示例**:

```json
{
  "quota_id": 1,
  "reset_type": "day"
}
```

**有效的reset_type值**:
- `minute`: 重置分钟计数器
- `hour`: 重置小时计数器
- `day`: 重置天数计数器
- `month`: 重置月计数器
- `total`: 重置总计数器
- `all`: 重置所有计数器

**响应示例**:

```json
{
  "success": true,
  "message": "Quota reset successfully",
  "quota_id": 1
}
```

### 7. 查询用户配额信息

**端点**: `POST /api/v1/tokens/quota/query`

**权限要求**:
- 学生/教师: 只能查询自己的配额
- 学校管理员: 可以查询学校内用户的配额
- 系统管理员: 可以查询任何用户的配额

**请求示例（查询自己的配额）**:

```json
{}
```

**请求示例（查询特定用户 - 仅管理员）**:

```json
{
  "user_id": 5
}
```

**响应示例**:

```json
{
  "user_id": 1,
  "username": "teacher1",
  "quota_id": 1,
  "quota_type": "user",
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "minute_used": 3,
  "hour_used": 25,
  "day_used": 150,
  "month_used": 500,
  "total_used": 1250,
  "minute_remaining": 7,
  "hour_remaining": 75,
  "day_remaining": 850,
  "month_remaining": 9500,
  "total_remaining": null,
  "description": "标准教师配额",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-31T10:30:00Z"
}
```

## 权限验证逻辑

### JWT Token权限验证

JWT Token使用基于角色的访问控制（RBAC）：

```python
# 系统管理端点
if current_user.role != "system_admin":
    raise HTTPException(status_code=403, detail="需要系统管理员权限")
```

### API Token权限验证

API Token使用细粒度权限控制：

```python
# 获取API Token
api_token = db.query(ApiToken).filter(
    ApiToken.user_id == current_user.id,
    ApiToken.is_active == True,
    ApiToken.is_revoked == False
).first()

# 检查系统管理权限
if not api_token.can_manage_system:
    raise HTTPException(
        status_code=403,
        detail="需要 manage_system 权限才能访问此端点"
    )
```

### 混合权限支持

系统同时支持JWT Token和API Token：

| 认证类型 | 权限机制 | 示例 |
|---------|---------|------|
| JWT Token | 角色权限 | `system_admin` 角色可访问所有系统管理功能 |
| API Token | 细粒度权限 | 需要 `manage_system` 权限才能访问系统管理功能 |

## 数据库变更

### ApiToken模型更新

```python
class ApiToken(Base):
    # ... 其他字段 ...

    # Permissions - 新增系统管理权限
    can_manage_system = Column(Boolean, default=False)
```

### 迁移文件

创建迁移: `5a4d43ed9d23_add_can_manage_system_to_api_tokens.py`

应用迁移:

```bash
cd backend
alembic upgrade head
```

## 使用场景

### 场景1: 外部系统集成

外部应用需要重载系统配置：

```python
import requests

# 使用具有 manage_system 权限的token
headers = {
    "Authorization": "Bearer hwtk_abc123..."
}

# 重载系统配置
response = requests.post(
    "http://localhost:8000/api/system/reload",
    headers=headers
)

print(response.json())
# {"message": "系统配置已重新加载", "reloaded": true}
```

### 场景2: 批量配额管理

为多个学生设置配额限制：

```python
import requests

headers = {
    "Authorization": "Bearer hwtk_abc123..."
}

# 批量设置配额
response = requests.post(
    "http://localhost:8000/api/v1/tokens/quota/batch-set",
    headers=headers,
    json={
        "user_ids": [1, 2, 3, 4, 5],
        "minute_limit": 10,
        "hour_limit": 100,
        "day_limit": 1000,
        "description": "标准学生配额"
    }
)

print(response.json())
# {"success": true, "message": "Batch quota update completed", "updated_count": 5}
```

### 场景3: 监控配额使用

查询用户配额使用情况：

```python
import requests

headers = {
    "Authorization": "Bearer hwtk_abc123..."
}

# 查询配额信息
response = requests.post(
    "http://localhost:8000/api/v1/tokens/quota/query",
    headers=headers,
    json={"user_id": 5}
)

quota_info = response.json()
print(f"已使用: {quota_info['day_used']}/{quota_info['day_limit']}")
print(f"剩余: {quota_info['day_remaining']}")
```

## 安全注意事项

1. **Token安全**
   - Token只在创建时显示一次，请妥善保存
   - 不要在代码中硬编码Token
   - 使用HTTPS传输Token

2. **权限最小化原则**
   - 只授予应用所需的最小权限
   - 定期审查和撤销不需要的Token
   - 为不同应用创建不同的Token

3. **过期管理**
   - 设置合理的Token过期时间
   - 过期Token无法使用，需要重新创建
   - 建议使用30天或更短的过期时间

4. **审计日志**
   - 所有Token使用都会记录在API Token表中
   - 包含使用次数、最后使用时间等信息
   - 定期检查异常使用情况

## 错误代码

| HTTP状态码 | 说明 | 解决方案 |
|-----------|------|---------|
| 401 | 认证失败 | 检查Token是否有效、是否过期 |
| 403 | 权限不足 | Token缺少所需权限，检查Token权限设置 |
| 404 | 资源不存在 | 检查请求的user_id、school_id是否正确 |
| 400 | 请求参数错误 | 检查请求参数格式和必需字段 |

## 相关文档

- [API Token管理文档](./docs/API_TOKEN_MANAGEMENT.md)
- [配额管理文档](./docs/QUOTA_MANAGEMENT.md)
- [系统管理文档](./docs/SYSTEM_MANAGEMENT.md)
- [后端开发指南](./DEVELOPMENT.md)

## 更新日志

### 2026-02-02
- ✅ 添加 `can_manage_system` 权限到 ApiToken 模型
- ✅ 更新系统管理端点支持Token权限验证
- ✅ 添加 `require_manage_system_permission` 权限验证函数
- ✅ 创建数据库迁移文件
- ✅ 更新Token创建和管理API以支持新权限
