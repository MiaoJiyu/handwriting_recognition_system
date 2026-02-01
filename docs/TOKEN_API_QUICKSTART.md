# Token API Quick Start Guide

## 概述

Token API 是一个基于 JWT 的外部应用接口,允许第三方应用安全地集成到字迹识别系统中。所有请求都需要在 HTTP 标头中携带 Authorization Token。

## 快速开始

### 1. 获取访问令牌

使用用户名和密码获取访问令牌:

```bash
curl -X POST http://localhost:8000/api/v1/tokens/create \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher1",
    "password": "password123",
    "app_name": "MyApp",
    "scope": "write"
  }'
```

响应示例:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "scope": "write",
  "user_info": {
    "id": 1,
    "username": "teacher1",
    "nickname": "张老师",
    "role": "teacher",
    "school_id": 1
  },
  "issued_at": "2026-01-31T10:30:00Z"
}
```

### 2. 使用令牌访问 API

在后续的所有请求中,将令牌添加到 Authorization 标头:

```http
Authorization: Bearer <access_token>
```

示例 - 获取用户信息:

```bash
curl -X GET http://localhost:8000/api/v1/tokens/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. 执行字迹识别

使用令牌进行字迹识别:

```bash
curl -X POST http://localhost:8000/api/recognition \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@test_image.jpg"
```

### 4. 上传样本

使用令牌上传样本图片:

```bash
curl -X POST http://localhost:8000/api/samples/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@sample_image.jpg"
```

---

## 权限作用域 (Scopes)

| 作用域 | 说明 | 最低用户角色 |
|--------|------|-------------|
| `read` | 只读访问 | **学生** |
| `write` | 读写访问 | **教师** |
| `admin` | 完全管理访问 | **学校管理员 / 系统管理员** |

### 权限限制

- **学生**: 只能请求 `read` 作用域
- **教师**: 可以请求 `read` 或 `write` 作用域
- **学校管理员**: 可以请求 `read`、`write` 或 `admin` 作用域
- **系统管理员**: 可以请求任何作用域

---

## Python 快速示例

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. 创建令牌
def create_token(username, password, app_name="MyApp", scope="write"):
    response = requests.post(
        f"{BASE_URL}/api/v1/tokens/create",
        json={
            "username": username,
            "password": password,
            "app_name": app_name,
            "scope": scope
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]

# 2. 执行识别
def recognize_handwriting(token, image_path):
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/api/recognition",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f}
        )
    response.raise_for_status()
    return response.json()

# 3. 上传样本
def upload_sample(token, image_path):
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/api/samples/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f}
        )
    response.raise_for_status()
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 获取令牌
    token = create_token("teacher1", "password123", "学习应用", "write")
    print(f"令牌: {token[:50]}...")

    # 获取当前用户
    user_info = requests.get(
        f"{BASE_URL}/api/v1/tokens/me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    print(f"当前用户: {user_info['username']} ({user_info['role']})")

    # 执行识别
    # result = recognize_handwriting(token, "test_image.jpg")
    # print(f"识别结果: {json.dumps(result, indent=2)}")

    # 上传样本
    # result = upload_sample(token, "sample_image.jpg")
    # print(f"上传结果: {json.dumps(result, indent=2)}")
```

---

## JavaScript 快速示例

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const BASE_URL = 'http://localhost:8000';

// 1. 创建令牌
async function createToken(username, password, appName = 'MyApp', scope = 'write') {
    const response = await axios.post(`${BASE_URL}/api/v1/tokens/create`, {
        username,
        password,
        app_name: appName,
        scope
    });
    return response.data.access_token;
}

// 2. 执行识别
async function recognizeHandwriting(token, imagePath) {
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));

    const response = await axios.post(`${BASE_URL}/api/recognition`, form, {
        headers: {
            ...form.getHeaders(),
            Authorization: `Bearer ${token}`
        }
    });
    return response.data;
}

// 3. 上传样本
async function uploadSample(token, imagePath) {
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));

    const response = await axios.post(`${BASE_URL}/api/samples/upload`, form, {
        headers: {
            ...form.getHeaders(),
            Authorization: `Bearer ${token}`
        }
    });
    return response.data;
}

// 使用示例
(async () => {
    try {
        // 获取令牌
        const token = await createToken('teacher1', 'password123', '学习应用', 'write');
        console.log(`令牌: ${token.substring(0, 50)}...`);

        // 获取当前用户
        const userInfo = await axios.get(`${BASE_URL}/api/v1/tokens/me`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        console.log(`当前用户: ${userInfo.data.username} (${userInfo.data.role})`);

    } catch (error) {
        console.error('错误:', error.response?.data || error.message);
    }
})();
```

---

## API 端点列表

| 方法 | 端点 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/tokens/create` | 创建访问令牌 | 否 |
| POST | `/api/v1/tokens/verify` | 验证令牌 | 否 |
| GET | `/api/v1/tokens/me` | 获取当前用户 | 是 |
| POST | `/api/v1/tokens/revoke` | 撤销令牌 | 是 |
| GET | `/api/v1/tokens/config` | 获取 API 配置 | 是 |
| GET | `/api/v1/tokens/info` | 获取 API 信息 | 否 |
| POST | `/api/recognition` | 执行字迹识别 | 是 |
| POST | `/api/samples/upload` | 上传样本 | 是 |
| GET | `/api/samples` | 列出样本 | 是 |
| GET | `/api/users/{user_id}` | 获取用户信息 | 是 |

---

## 错误处理

常见错误代码:

| 状态码 | 说明 |
|--------|------|
| 401 | 认证失败 - 用户名或密码错误 |
| 403 | 权限不足 - 用户角色不支持请求的作用域 |
| 404 | 资源未找到 |
| 413 | 文件过大 - 超过上传限制 (默认 10MB) |
| 500 | 服务器错误 |

错误响应格式:

```json
{
  "detail": "错误描述信息"
}
```

---

## 安全建议

1. **保护令牌**: 不要在客户端代码中暴露令牌
2. **使用 HTTPS**: 生产环境必须使用 HTTPS
3. **最小权限**: 只请求应用程序所需的最小作用域
4. **令牌管理**: 及时撤销不再使用的令牌
5. **处理过期**: 实现令牌刷新逻辑或提示用户重新认证

---

## 完整文档

详细的 API 文档请参考:

- **Token API 文档**: `/opt/handwriting_recognition_system/docs/TOKEN_API.md`
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 技术支持

如遇问题,请查阅:

- 项目 README: `/opt/handwriting_recognition_system/README.md`
- 开发指南: `/opt/handwriting_recognition_system/docs/DEVELOPMENT.md`
- API 文档: `/opt/handwriting_recognition_system/docs/TOKEN_API.md`
