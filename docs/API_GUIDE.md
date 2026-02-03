# API使用指南 (API Usage Guide)

**版本**: 2.0
**最后更新**: 2026-02-02

---

## 目录

1. [快速开始](#快速开始)
2. [认证](#认证)
3. [用户管理](#用户管理)
4. [学校管理](#学校管理)
5. [样本管理](#样本管理)
6. [识别](#识别)
7. [训练](#训练)
8. [外部Token API](#外部token-api)
9. [错误处理](#错误处理)
10. [配额管理](#配额管理)
11. [系统配置](#系统配置)

---

## 快速开始

### 基础URL

```
开发环境: http://localhost:8000
API文档: http://localhost:8000/docs
健康检查: http://localhost:8000/health
```

### 认证流程

所有API请求（除公开端点外）都需要在请求头中携带认证token：

```
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## 认证

### 1. 用户登录

使用用户名和密码登录，获取访问令牌。

**请求**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "nickname": "系统管理员",
    "role": "system_admin",
    "school_id": null
  }
}
```

### 2. 获取当前用户信息

**请求**:
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 修改密码

**请求**:
```bash
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "admin123",
    "new_password": "newpassword123"
  }'
```

### 4. 用户登出

**请求**:
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**注意**: 登出后，前端应删除本地存储的token。

---

## 用户管理

### 1. 创建用户

**请求**:
```bash
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher1",
    "password": "password123",
    "nickname": "张老师",
    "role": "teacher",
    "school_id": 1
  }'
```

**角色说明**:
- `student`: 学生
- `teacher`: 教师
- `school_admin`: 学校管理员
- `system_admin`: 系统管理员

### 2. 获取用户列表

**请求**:
```bash
curl -X GET http://localhost:8000/api/users \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 获取用户详情

**请求**:
```bash
curl -X GET http://localhost:8000/api/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 更新用户

**请求**:
```bash
curl -X PUT http://localhost:8000/api/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nickname": "新昵称"
  }'
```

### 5. 删除用户

**请求**:
```bash
curl -X DELETE http://localhost:8000/api/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. 批量创建学生

**请求**:
```bash
curl -X POST http://localhost:8000/api/users/batch-create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "count": 5,
    "school_id": 1,
    "prefix": "2024"
  }'
```

### 7. 导出用户列表

**请求**:
```bash
curl -X GET http://localhost:8000/api/users/export \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o users.xlsx
```

---

## 学校管理

### 1. 创建学校

**请求**:
```bash
curl -X POST http://localhost:8000/api/schools \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "第一中学"
  }'
```

### 2. 获取学校列表

**请求**:
```bash
curl -X GET http://localhost:8000/api/schools \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 更新学校

**请求**:
```bash
curl -X PUT http://localhost:8000/api/schools/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "第一中学（更新）"
  }'
```

### 4. 删除学校

**请求**:
```bash
curl -X DELETE http://localhost:8000/api/schools/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**注意**: 学校下有用户时无法删除。

---

## 样本管理

### 1. 上传样本

**请求**:
```bash
curl -X POST http://localhost:8000/api/samples/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sample.jpg"
```

**限制**:
- 文件大小: 最大10MB
- 文件类型: 仅支持图片格式

### 2. 获取样本列表

**请求**:
```bash
curl -X GET "http://localhost:8000/api/samples?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 获取样本详情

**请求**:
```bash
curl -X GET http://localhost:8000/api/samples/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 手动裁剪样本

**请求**:
```bash
curl -X POST http://localhost:8000/api/samples/1/crop \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bbox": {
      "x": 10,
      "y": 20,
      "width": 100,
      "height": 50
    }
  }'
```

### 5. 删除样本

**请求**:
```bash
curl -X DELETE http://localhost:8000/api/samples/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 识别

### 1. 单张图片识别

**请求**:
```bash
curl -X POST http://localhost:8000/api/recognition \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.jpg"
```

**响应**:
```json
{
  "result": {
    "user_id": 123,
    "username": "张三",
    "confidence": 0.95,
    "is_unknown": false,
    "top_k": [
      {
        "user_id": 123,
        "username": "张三",
        "score": 0.95
      },
      {
        "user_id": 456,
        "username": "李四",
        "score": 0.85
      }
    ]
  },
  "sample_id": null,
  "created_at": "2026-02-02T10:30:00"
}
```

### 2. 批量识别

**请求**:
```bash
curl -X POST http://localhost:8000/api/recognition/batch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@test1.jpg" \
  -F "files=@test2.jpg"
```

---

## 训练

### 1. 开始训练

**请求**:
```bash
curl -X POST http://localhost:8000/api/training/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_retrain": false
  }'
```

**参数说明**:
- `force_retrain`: 是否强制重新训练（false表示仅在有新样本时训练）

### 2. 查询训练状态

**请求**:
```bash
curl -X GET http://localhost:8000/api/training/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应**:
```json
{
  "status": "completed",
  "progress": 100,
  "message": "训练完成"
}
```

**状态说明**:
- `pending`: 等待开始
- `running`: 训练中
- `completed`: 训练完成
- `failed`: 训练失败

---

## 外部Token API

### 1. 创建外部Token

用于外部应用集成，支持作用域（scope）控制。

**请求**:
```bash
curl -X POST http://localhost:8000/api/v1/tokens/create \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher1",
    "password": "password123",
    "app_name": "My App",
    "app_version": "1.0.0",
    "scope": "write"
  }'
```

**作用域（Scope）说明**:
- `read`: 仅读取权限
- `write`: 读写权限
- `admin`: 完整权限

### 2. 验证Token

**请求**:
```bash
curl -X POST http://localhost:8000/api/v1/tokens/verify \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN"
  }'
```

### 3. 获取API配置

**请求**:
```bash
curl -X GET http://localhost:8000/api/v1/tokens/config \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应**:
```json
{
  "version": "2.0.0",
  "base_url": "http://localhost:8000",
  "endpoints": {
    "token_create": "/api/v1/tokens/create",
    "token_verify": "/api/v1/tokens/verify",
    "recognition": "/api/recognition",
    "samples": "/api/samples",
    "samples_upload": "/api/samples/upload",
    "users": "/api/users",
    "training": "/api/training"
  },
  "limits": {
    "max_upload_size": 10485760,
    "token_expiry_minutes": 30
  },
  "supported_scopes": ["read", "write", "admin"],
  "supported_roles": ["student", "teacher", "school_admin", "system_admin"]
}
```

---

## 错误处理

所有API错误响应遵循统一格式：

### 统一错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "errors": {
    "field": "具体字段错误"
  },
  "timestamp": "2026-02-02T10:30:00Z"
}
```

### HTTP状态码说明

| 状态码 | 说明 | 示例场景 |
|--------|------|---------|
| 200 | 成功 | 正常请求成功处理 |
| 201 | 创建成功 | 资源创建成功 |
| 400 | 请求错误 | 参数缺失或格式错误 |
| 401 | 未授权 | Token无效或缺失 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 409 | 冲突 | 资源已存在 |
| 413 | 文件过大 | 上传文件超过大小限制 |
| 422 | 验证失败 | 数据验证不通过 |
| 429 | 请求过多 | 配额用尽或限流 |
| 500 | 服务器错误 | 内部服务器错误 |

### 常见错误示例

#### 1. Token无效

```json
{
  "success": false,
  "message": "无效的认证令牌",
  "timestamp": "2026-02-02T10:30:00Z"
}
```

#### 2. 文件过大

```json
{
  "success": false,
  "message": "文件大小不能超过 10MB",
  "timestamp": "2026-02-02T10:30:00Z"
}
```

#### 3. 权限不足

```json
{
  "success": false,
  "message": "无权执行此操作",
  "timestamp": "2026-02-02T10:30:00Z"
}
```

#### 4. 配额超限

```json
{
  "success": false,
  "message": "识别次数超限",
  "errors": {
    "deny_reason": "day_limit",
    "usage": {
      "day_used": 100,
      "day_limit": 100
    }
  },
  "timestamp": "2026-02-02T10:30:00Z"
}
```

---

## 配额管理

### 1. 获取配额信息

**请求**:
```bash
curl -X GET http://localhost:8000/api/quotas/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 设置配额（管理员）

**请求**:
```bash
curl -X POST http://localhost:8000/api/quotas \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quota_type": "user",
    "user_id": 1,
    "minute_limit": 10,
    "hour_limit": 100,
    "day_limit": 1000,
    "month_limit": 10000
  }'
```

---

## 系统配置

### 1. 获取系统配置

**请求**:
```bash
curl -X GET http://localhost:8000/api/system/config \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应**:
```json
{
  "database_url": "mysql+pymysql://...",
  "inference_service": "localhost:50051",
  "redis": "localhost:6379",
  "upload_dir": "./uploads",
  "samples_dir": "./uploads/samples",
  "models_dir": "./models",
  "max_upload_size": 10485760,
  "cors_origins": "http://localhost:3000,http://localhost:5173"
}
```

### 2. 重载系统配置

**请求**:
```bash
curl -X POST http://localhost:8000/api/system/reload \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**注意**: 重载配置需要系统管理员权限。

---

## 最佳实践

### 1. Token管理

- 妥善保存token，避免泄露
- Token默认有效期30分钟，过期后需重新登录
- 前端应在登出时删除本地存储的token

### 2. 错误处理

- 检查响应中的`success`字段
- 根据`errors`字段显示具体错误信息
- HTTP状态码是主要判断依据

### 3. 文件上传

- 检查文件大小后再上传（最大10MB）
- 确保文件格式正确（仅支持图片）
- 上传大文件时显示进度

### 4. 分页

- 使用`page`和`page_size`参数进行分页
- 默认每页20条记录

---

## Python客户端示例

```python
import requests
import json

class HandwritingAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None

    def login(self, username, password):
        """登录"""
        data = {
            "username": username,
            "password": password
        }
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            data=data
        )
        result = response.json()
        self.token = result.get("access_token")
        return result

    def recognize(self, image_path):
        """识别图片"""
        files = {"file": open(image_path, "rb")}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/recognition",
            files=files,
            headers=headers
        )
        return response.json()

    def upload_sample(self, image_path, student_id=None):
        """上传样本"""
        files = {"file": open(image_path, "rb")}
        data = {}
        if student_id:
            data["student_id"] = student_id
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/samples/upload",
            files=files,
            data=data,
            headers=headers
        )
        return response.json()

# 使用示例
api = HandwritingAPI()
api.login("admin", "admin123")

result = api.recognize("test.jpg")
print(f"识别结果: {result}")
```

---

## JavaScript/Node.js客户端示例

```javascript
const axios = require('axios');

class HandwritingAPI {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await axios.post(
      `${this.baseUrl}/api/auth/login`,
      formData
    );
    this.token = response.data.access_token;
    return response.data;
  }

  async recognize(imagePath) {
    const formData = new FormData();
    formData.append('file', require('fs').createReadStream(imagePath));

    const response = await axios.post(
      `${this.baseUrl}/api/recognition`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    return response.data;
  }

  async uploadSample(imagePath, studentId = null) {
    const formData = new FormData();
    formData.append('file', require('fs').createReadStream(imagePath));
    if (studentId) {
      formData.append('student_id', studentId);
    }

    const response = await axios.post(
      `${this.baseUrl}/api/samples/upload`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    return response.data;
  }
}

// 使用示例
(async () => {
  const api = new HandwritingAPI();
  await api.login('admin', 'admin123');

  const result = await api.recognize('test.jpg');
  console.log('识别结果:', result);
})();
```

---

## 故障排除

### 问题1: 无法连接到API

**解决方案**:
- 检查后端服务是否运行
- 检查防火墙设置
- 检查CORS配置

### 问题2: Token过期

**解决方案**:
- 重新登录获取新token
- 检查`ACCESS_TOKEN_EXPIRE_MINUTES`配置

### 问题3: 文件上传失败

**解决方案**:
- 检查文件大小（最大10MB）
- 检查文件格式
- 检查磁盘空间

### 问题4: 识别结果总是未知

**解决方案**:
- 确认已完成训练
- 检查样本是否足够（至少每个用户2-3个样本）
- 查看推理服务日志

---

## 更多资源

- **API文档**: http://localhost:8000/docs
- **项目文档**: `/docs/`目录
- **整合计划**: `INTEGRATION_PLAN.md`
- **改进计划**: `IMPROVEMENT_PLAN_PHASE2.md`

---

**文档版本**: 2.0
**最后更新**: 2026-02-02
