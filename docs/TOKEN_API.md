# Token API Documentation

## Overview

The Token API provides external applications with a secure way to integrate with the Handwriting Recognition System. It uses JWT (JSON Web Token) based authentication with role-based access control (RBAC) and scoping for fine-grained permissions.

## Base URL

```
http://localhost:8000/api/v1/tokens
```

**API Documentation:** `http://localhost:8000/docs` (Swagger UI)
**ReDoc Documentation:** `http://localhost:8000/redoc`

---

## Authentication

All API requests must include the access token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

### Token Lifecycle

1. **Create Token**: Obtain an access token by calling `/api/v1/tokens/create`
2. **Use Token**: Include the token in the `Authorization` header for all subsequent requests
3. **Verify Token**: Check if a token is valid using `/api/v1/tokens/verify`
4. **Revoke Token**: Invalidate a token using `/api/v1/tokens/revoke`

---

## Scopes and Permissions

The API supports three token scopes that determine what operations a token can perform:

| Scope | Description | Minimum User Role | Allowed Operations |
|-------|-------------|-------------------|---------------------|
| `read` | Read-only access | **Student** | View samples, users, recognition logs |
| `write` | Read and write access | **Teacher** | Upload samples, perform recognition, read operations |
| `admin` | Full administrative access | **School Admin / System Admin** | All operations including user management, school management |

### Scope Validation Rules

- **Student**: Can only request `read` scope
- **Teacher**: Can request `read` or `write` scope
- **School Admin**: Can request `read`, `write`, or `admin` scope
- **System Admin**: Can request any scope

If a user requests a scope that exceeds their role permissions, the API will return a `403 Forbidden` error.

---

## API Endpoints

### 1. Create Access Token

Generate an access token for external application integration.

**Endpoint:** `POST /api/v1/tokens/create`

**Authentication:** None (credentials in request body)

**Request Body:**

```json
{
  "username": "teacher1",
  "password": "password123",
  "app_name": "My Learning App",
  "app_version": "1.0.0",
  "scope": "write"
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | System username (student/teacher/admin) |
| password | string | Yes | User password |
| app_name | string | Yes | Application name for tracking |
| app_version | string | No | Application version (optional) |
| scope | string | No | Token scope: `read`, `write`, or `admin` (default: `read`) |

**Success Response (201 Created):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZWFjaGVyMSIsInJvbGUiOiJ0ZWFjaGVyIiwic2NvcGUiOiJ3cml0ZSIsImFwcF9uYW1lIjoiTXkgTGVhcm5pbmcgQXBwIiwiZXhwIjoxNzY0ODQ4NjAwfQ.signature",
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

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 401 Unauthorized | Invalid username or password |
| 403 Forbidden | User role cannot request the specified scope |

---

### 2. Verify Token

Verify if an access token is valid and retrieve user information.

**Endpoint:** `POST /api/v1/tokens/verify`

**Authentication:** None (token in request body)

**Request Body:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200 OK):**

```json
{
  "valid": true,
  "user_info": {
    "id": 1,
    "username": "teacher1",
    "nickname": "张老师",
    "role": "teacher",
    "school_id": 1,
    "scope": "write"
  },
  "expires_at": "2026-01-31T11:00:00Z"
}
```

**Invalid Token Response (200 OK):**

```json
{
  "valid": false,
  "error": "Token has expired"
}
```

---

### 3. Get Current User

Retrieve information about the user associated with the current token.

**Endpoint:** `GET /api/v1/tokens/me`

**Authentication:** Bearer Token required

**Request Headers:**

```http
Authorization: Bearer <access_token>
```

**Success Response (200 OK):**

```json
{
  "id": 1,
  "username": "teacher1",
  "nickname": "张老师",
  "role": "teacher",
  "school_id": 1,
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

### 4. Revoke Token

Revoke the current access token.

**Endpoint:** `POST /api/v1/tokens/revoke`

**Authentication:** Bearer Token required

**Request Headers:**

```http
Authorization: Bearer <access_token>
```

**Success Response (200 OK):**

```json
{
  "message": "Token revoked successfully. Please discard this token.",
  "status": "success",
  "timestamp": "2026-01-31T10:30:00Z"
}
```

**Note:** After revocation, the client should discard the token and obtain a new one if needed.

---

### 5. Get API Configuration

Retrieve API configuration information for external applications.

**Endpoint:** `GET /api/v1/tokens/config`

**Authentication:** Bearer Token required

**Request Headers:**

```http
Authorization: Bearer <access_token>
```

**Success Response (200 OK):**

```json
{
  "version": "1.0.0",
  "base_url": "http://localhost:8000",
  "endpoints": {
    "token_create": "/api/v1/tokens/create",
    "token_verify": "/api/v1/tokens/verify",
    "recognition": "/api/recognition",
    "samples": "/api/samples",
    "samples_upload": "/api/samples/upload",
    "users": "/api/users",
    "users_me": "/api/auth/me",
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

### 6. Get API Information (Public)

Retrieve public API information without authentication.

**Endpoint:** `GET /api/v1/tokens/info`

**Authentication:** None

**Success Response (200 OK):**

```json
{
  "name": "Handwriting Recognition Token API",
  "version": "1.0.0",
  "description": "External API for handwriting recognition system integration",
  "authentication": "Bearer Token",
  "base_url": "http://localhost:8000",
  "documentation": "/docs",
  "endpoints": [
    "/api/v1/tokens/create (POST)",
    "/api/v1/tokens/verify (POST)",
    "/api/v1/tokens/me (GET)",
    "/api/v1/tokens/revoke (POST)",
    "/api/v1/tokens/config (GET)",
    "/api/v1/tokens/info (GET)"
  ],
  "scopes": {
    "read": "View samples, users, recognition logs",
    "write": "Upload samples, perform recognition",
    "admin": "Full administrative access"
  },
  "roles": {
    "student": "Can only access own data",
    "teacher": "Can manage students and perform recognition",
    "school_admin": "Can manage school users",
    "system_admin": "Full system access"
  }
}
```

---

## Using the Token with Other API Endpoints

Once you have obtained an access token, you can use it to access other API endpoints:

### Handwriting Recognition

**Endpoint:** `POST /api/recognition`

**Request Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body:** Send the image file as `file` parameter

### Upload Sample

**Endpoint:** `POST /api/samples/upload`

**Request Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body:** Send the image file as `file` parameter

### List Samples

**Endpoint:** `GET /api/samples`

**Request Headers:**

```http
Authorization: Bearer <access_token>
```

**Query Parameters:** `user_id`, `limit`, `offset`

### Get User Information

**Endpoint:** `GET /api/users/{user_id}`

**Request Headers:**

```http
Authorization: Bearer <access_token>
```

---

## Usage Examples

### Python Example

```python
import requests
import base64
import json

# Base URL
BASE_URL = "http://localhost:8000"

def create_token(username, password, app_name="MyApp", scope="write"):
    """Create an access token"""
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

def verify_token(token):
    """Verify if a token is valid"""
    response = requests.post(
        f"{BASE_URL}/api/v1/tokens/verify",
        json={"token": token}
    )
    return response.json()

def get_current_user(token):
    """Get current user information"""
    response = requests.get(
        f"{BASE_URL}/api/v1/tokens/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()

def recognize_handwriting(token, image_path):
    """Perform handwriting recognition"""
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/api/recognition",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f}
        )
    response.raise_for_status()
    return response.json()

def upload_sample(token, image_path, user_id=None):
    """Upload a sample image"""
    with open(image_path, "rb") as f:
        data = {"user_id": str(user_id)} if user_id else {}
        response = requests.post(
            f"{BASE_URL}/api/samples/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f},
            data=data
        )
    response.raise_for_status()
    return response.json()

# Example usage
if __name__ == "__main__":
    # 1. Create token
    token = create_token("teacher1", "password123", "LearningApp", "write")
    print(f"Token: {token[:50]}...")

    # 2. Verify token
    verify_result = verify_token(token)
    print(f"Token valid: {verify_result['valid']}")

    # 3. Get current user
    user_info = get_current_user(token)
    print(f"Current user: {user_info['username']} ({user_info['role']})")

    # 4. Perform recognition
    # recognition_result = recognize_handwriting(token, "test_image.jpg")
    # print(f"Recognition result: {json.dumps(recognition_result, indent=2)}")

    # 5. Upload sample
    # upload_result = upload_sample(token, "sample_image.jpg")
    # print(f"Upload result: {json.dumps(upload_result, indent=2)}")

    # 6. Revoke token
    # revoke_response = requests.post(
    #     f"{BASE_URL}/api/v1/tokens/revoke",
    #     headers={"Authorization": f"Bearer {token}"}
    # )
    # print(f"Revoke response: {revoke_response.json()['message']}")
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const BASE_URL = 'http://localhost:8000';

async function createToken(username, password, appName = 'MyApp', scope = 'write') {
    const response = await axios.post(`${BASE_URL}/api/v1/tokens/create`, {
        username,
        password,
        app_name: appName,
        scope
    });
    return response.data.access_token;
}

async function verifyToken(token) {
    const response = await axios.post(`${BASE_URL}/api/v1/tokens/verify`, {
        token
    });
    return response.data;
}

async function getCurrentUser(token) {
    const response = await axios.get(`${BASE_URL}/api/v1/tokens/me`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
}

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

async function uploadSample(token, imagePath, userId = null) {
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));
    if (userId) {
        form.append('user_id', userId.toString());
    }

    const response = await axios.post(`${BASE_URL}/api/samples/upload`, form, {
        headers: {
            ...form.getHeaders(),
            Authorization: `Bearer ${token}`
        }
    });
    return response.data;
}

// Example usage
(async () => {
    try {
        // 1. Create token
        const token = await createToken('teacher1', 'password123', 'LearningApp', 'write');
        console.log(`Token: ${token.substring(0, 50)}...`);

        // 2. Verify token
        const verifyResult = await verifyToken(token);
        console.log(`Token valid: ${verifyResult.valid}`);

        // 3. Get current user
        const userInfo = await getCurrentUser(token);
        console.log(`Current user: ${userInfo.username} (${userInfo.role})`);

        // 4. Perform recognition
        // const recognitionResult = await recognizeHandwriting(token, 'test_image.jpg');
        // console.log('Recognition result:', JSON.stringify(recognitionResult, null, 2));

        // 5. Upload sample
        // const uploadResult = await uploadSample(token, 'sample_image.jpg');
        // console.log('Upload result:', JSON.stringify(uploadResult, null, 2));

    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
})();
```

### cURL Examples

```bash
# 1. Create token
curl -X POST http://localhost:8000/api/v1/tokens/create \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher1",
    "password": "password123",
    "app_name": "MyApp",
    "scope": "write"
  }'

# 2. Verify token (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/v1/tokens/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'

# 3. Get current user (replace TOKEN with actual token)
curl -X GET http://localhost:8000/api/v1/tokens/me \
  -H "Authorization: Bearer TOKEN"

# 4. Revoke token (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/v1/tokens/revoke \
  -H "Authorization: Bearer TOKEN"

# 5. Get API configuration (replace TOKEN with actual token)
curl -X GET http://localhost:8000/api/v1/tokens/config \
  -H "Authorization: Bearer TOKEN"

# 6. Get API info (public endpoint)
curl -X GET http://localhost:8000/api/v1/tokens/info

# 7. Perform recognition with token (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/recognition \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test_image.jpg"

# 8. Upload sample with token (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/samples/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@sample_image.jpg"
```

---

## Error Handling

All API endpoints return standard HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| 200 OK | Request successful |
| 201 Created | Resource created successfully |
| 400 Bad Request | Invalid request parameters |
| 401 Unauthorized | Authentication failed or token missing/invalid |
| 403 Forbidden | Insufficient permissions |
| 404 Not Found | Resource not found |
| 413 Payload Too Large | File upload exceeds size limit |
| 500 Internal Server Error | Server error |

**Error Response Format:**

```json
{
  "detail": "Error message here"
}
```

---

## Token Security Best Practices

1. **Keep tokens secure**: Store tokens securely and never expose them in client-side code
2. **Use HTTPS**: Always use HTTPS in production to prevent token interception
3. **Set appropriate scopes**: Request only the minimum scope needed for your application
4. **Revoke tokens**: Revoke tokens when they are no longer needed
5. **Handle expiration**: Implement token refresh logic or prompt users to re-authenticate
6. **Rate limiting**: Implement rate limiting on your application to prevent abuse

---

## Rate Limiting

Currently, the API does not enforce rate limiting. In a production environment, you should implement rate limiting based on:
- Token ID (per-token rate limits)
- IP address (per-IP rate limits)
- User ID (per-user rate limits)

---

## Support and Documentation

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Project README**: `/opt/handwriting_recognition_system/README.md`
- **Development Guide**: `/opt/handwriting_recognition_system/docs/DEVELOPMENT.md`

---

## Changelog

### Version 1.0.0 (2026-01-31)

- Initial release of Token API
- Support for token creation, verification, revocation
- Role-based access control with scoping
- Integration with existing authentication system
