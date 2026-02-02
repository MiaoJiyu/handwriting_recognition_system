# 字迹识别调用次数与速率限制功能

## 功能概述

本系统实现了完整的字迹识别调用次数与速率限制功能，支持多层级配额管理和灵活的限流策略。

### 主要特性

1. **多时间窗口限制**：支持每分钟、每小时、每天、每月、总次数限制
2. **层级配额管理**：系统管理员 → 学校管理员 → 用户
3. **批量配额设置**：支持批量为多个用户/学校设置配额
4. **Token API 支持**：允许通过 Token API 修改配额限制
5. **实时使用统计**：实时查看配额使用情况和告警
6. **配额使用日志**：记录每次识别请求的配额使用情况

## 配额类型

### 用户配额
- 适用于单个用户
- 由系统管理员或学校管理员配置
- 学校管理员只能配置自己学校内的用户配额

### 学校配额
- 适用于整个学校
- 仅由系统管理员配置
- 用于限制学校级别的总识别次数

## 时间窗口限制

| 时间窗口 | 说明 | 默认值 |
|---------|------|--------|
| minute_limit | 每分钟最多识别次数 | 0（无限制） |
| hour_limit | 每小时最多识别次数 | 0（无限制） |
| day_limit | 每天最多识别次数 | 0（无限制） |
| month_limit | 每月最多识别次数 | 0（无限制） |
| total_limit | 总计最多识别次数 | 0（无限制） |

**注意**：限制值设置为 0 表示无限制。

## 权限管理

### 系统管理员
- 可以配置任何用户或学校的配额
- 可以批量设置多个用户/学校的配额
- 可以重置任何配额的使用计数
- 可以删除任何配额

### 学校管理员
- 只能配置自己学校内用户的配额
- 只能批量设置自己学校内用户的配额
- 只能重置自己学校内用户的配额
- 不能配置学校配额

### 老师
- 可以查看自己的配额使用情况
- 不能修改配额

### 学生
- 不能查看配额信息
- 不能修改配额

## API 端点

### 1. 配额管理 API

#### 获取配额列表
```
GET /api/quotas
```

**查询参数**：
- `quota_type`: 配额类型（user 或 school）
- `user_id`: 用户 ID
- `school_id`: 学校 ID

#### 获取单个配额
```
GET /api/quotas/{quota_id}
```

#### 创建配额
```
POST /api/quotas
Content-Type: application/json

{
  "quota_type": "user",
  "user_id": 1,
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "description": "标准学生配额"
}
```

#### 更新配额
```
PUT /api/quotas/{quota_id}
Content-Type: application/json

{
  "minute_limit": 20,
  "hour_limit": 200,
  "day_limit": 2000,
  "month_limit": 20000,
  "total_limit": 0,
  "description": "升级后的配额"
}
```

#### 批量更新配额
```
POST /api/quotas/batch-update
Content-Type: application/json

{
  "user_ids": [1, 2, 3, 4, 5],
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "description": "批量更新学生配额"
}
```

#### 重置配额使用计数
```
POST /api/quotas/{quota_id}/reset
Content-Type: application/json

{
  "reset_type": "all"  // "minute", "hour", "day", "month", "total", "all"
}
```

#### 删除配额
```
DELETE /api/quotas/{quota_id}
```

#### 获取配额使用日志
```
GET /api/quotas/{quota_id}/logs?limit=100
```

### 2. Token API 配额管理

#### 通过 Token 设置配额
```
POST /api/v1/tokens/quota/set
Authorization: Bearer <token>
Content-Type: application/json

{
  "quota_type": "user",
  "user_id": 5,
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "description": "通过 API 设置的配额"
}
```

#### 通过 Token 批量设置配额
```
POST /api/v1/tokens/quota/batch-set
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_ids": [1, 2, 3, 4, 5],
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "description": "通过 API 批量设置的配额"
}
```

#### 通过 Token 重置配额
```
POST /api/v1/tokens/quota/reset
Authorization: Bearer <token>
Content-Type: application/json

{
  "quota_id": 1,
  "reset_type": "day"
}
```

### 3. 识别 API 集成

识别 API (`POST /api/recognition`) 会自动检查配额：
- 配额足够：正常处理识别请求
- 配额不足：返回 HTTP 429 错误，包含使用详情

**配额不足响应示例**：
```json
{
  "detail": "识别次数超限",
  "deny_reason": "day_limit",
  "usage": {
    "minute_used": 45,
    "minute_limit": 10,
    "hour_used": 120,
    "hour_limit": 100,
    "day_used": 1050,
    "day_limit": 1000,
    "month_used": 15000,
    "month_limit": 10000,
    "total_used": 5000,
    "total_limit": 0
  }
}
```

## 前端使用

### 配额管理页面

访问路径：`/quotas`

**功能**：
1. 查看所有配额列表
2. 查看配额使用情况（带颜色告警）
3. 创建新配额
4. 编辑现有配额
5. 批量设置用户配额
6. 重置配额使用计数
7. 查看配额使用日志

**使用状态指示**：
- 绿色：使用量正常（< 80%）
- 橙色：接近限制（80% - 100%）
- 红色：已超限（> 100%）

## 配额检查逻辑

### 检查流程

1. 获取用户配额
2. 如果有学校 ID，同时获取学校配额
3. 检查时间窗口是否需要重置
4. 逐项检查限制（分钟、小时、天、月、总计）
5. 如果有任何一项超限，拒绝请求
6. 如果所有项都通过，允许请求

### 时间窗口重置规则

- **分钟**：当前时间与上次重置时间间隔 >= 60 秒
- **小时**：当前时间与上次重置时间间隔 >= 3600 秒
- **天**：当前日期与上次重置日期不同
- **月**：当前月份与上次重置月份不同

## 配额使用日志

每次识别请求都会记录配额使用日志：

| 字段 | 说明 |
|------|------|
| id | 日志 ID |
| user_id | 用户 ID |
| school_id | 学校 ID |
| quota_type | 配额类型 |
| quota_id | 配额 ID |
| recognition_log_id | 识别日志 ID |
| is_allowed | 是否允许（1=允许，0=拒绝） |
| deny_reason | 拒绝原因（分钟/小时/天/月/总计） |
| usage_snapshot | 配额使用快照（拒绝时） |
| created_at | 创建时间 |

## 数据库表结构

### quotas 表

```sql
CREATE TABLE quotas (
  id INT PRIMARY KEY AUTO_INCREMENT,
  quota_type VARCHAR(20) NOT NULL,  -- 'user' 或 'school'
  user_id INT NULL,
  school_id INT NULL,
  minute_limit INT DEFAULT 0 NOT NULL,
  hour_limit INT DEFAULT 0 NOT NULL,
  day_limit INT DEFAULT 0 NOT NULL,
  month_limit INT DEFAULT 0 NOT NULL,
  total_limit INT DEFAULT 0 NOT NULL,
  minute_used INT DEFAULT 0 NOT NULL,
  hour_used INT DEFAULT 0 NOT NULL,
  day_used INT DEFAULT 0 NOT NULL,
  month_used INT DEFAULT 0 NOT NULL,
  total_used INT DEFAULT 0 NOT NULL,
  minute_reset_at DATETIME NULL,
  hour_reset_at DATETIME NULL,
  day_reset_at DATETIME NULL,
  month_reset_at DATETIME NULL,
  description VARCHAR(500) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_quota_type_user_id (quota_type, user_id),
  INDEX ix_quota_type_school_id (quota_type, school_id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (school_id) REFERENCES schools(id)
);
```

### quota_usage_logs 表

```sql
CREATE TABLE quota_usage_logs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,
  school_id INT NULL,
  quota_type VARCHAR(20) NOT NULL,
  quota_id INT NULL,
  recognition_log_id INT NULL,
  is_allowed INT DEFAULT 1 NOT NULL,
  deny_reason VARCHAR(100) NULL,
  usage_snapshot JSON NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_quota_usage_user_created (user_id, created_at),
  INDEX ix_quota_usage_school_created (school_id, created_at),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (school_id) REFERENCES schools(id),
  FOREIGN KEY (recognition_log_id) REFERENCES recognition_logs(id)
);
```

## 使用示例

### 示例 1：为学生设置配额

```bash
curl -X POST http://localhost:8000/api/quotas \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "quota_type": "user",
    "user_id": 5,
    "minute_limit": 10,
    "hour_limit": 100,
    "day_limit": 1000,
    "month_limit": 10000,
    "total_limit": 0,
    "description": "标准学生配额"
  }'
```

### 示例 2：批量设置班级配额

```bash
curl -X POST http://localhost:8000/api/quotas/batch-update \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "minute_limit": 5,
    "hour_limit": 50,
    "day_limit": 500,
    "month_limit": 5000,
    "total_limit": 0,
    "description": "一班学生配额"
  }'
```

### 示例 3：通过 Token API 设置配额

```bash
curl -X POST http://localhost:8000/api/v1/tokens/quota/set \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "quota_type": "user",
    "user_id": 15,
    "minute_limit": 20,
    "hour_limit": 200,
    "day_limit": 2000,
    "month_limit": 20000,
    "total_limit": 0,
    "description": "VIP 用户配额"
  }'
```

### 示例 4：查看配额使用情况

```bash
curl -X GET http://localhost:8000/api/quotas/1 \
  -H "Authorization: Bearer <admin_token>"
```

**响应**：
```json
{
  "id": 1,
  "quota_type": "user",
  "user_id": 5,
  "school_id": 1,
  "minute_limit": 10,
  "hour_limit": 100,
  "day_limit": 1000,
  "month_limit": 10000,
  "total_limit": 0,
  "minute_used": 45,
  "hour_used": 120,
  "day_used": 1050,
  "month_used": 15000,
  "total_used": 5000,
  "minute_reset_at": "2026-02-01T15:30:00",
  "hour_reset_at": "2026-02-01T15:00:00",
  "day_reset_at": "2026-02-01T00:00:00",
  "month_reset_at": "2026-02-01T00:00:00",
  "description": "标准学生配额",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-02-01T10:00:00"
}
```

## 最佳实践

### 配额设置建议

1. **学生用户**
   - 每分钟：5-10 次
   - 每小时：50-100 次
   - 每天：500-1000 次
   - 每月：5000-10000 次

2. **老师用户**
   - 每分钟：10-20 次
   - 每小时：100-200 次
   - 每天：1000-2000 次
   - 每月：10000-20000 次

3. **学校配额**
   - 根据学校规模设置
   - 通常为所有学生配额总和的 2-3 倍

### 监控与告警

1. 定期检查配额使用情况
2. 当使用量接近 80% 时发出告警
3. 及时为高频用户调整配额
4. 记录配额调整历史

### 性能优化

1. 使用索引优化查询性能
2. 定期清理旧的配额使用日志
3. 考虑使用 Redis 缓存配额数据

## 故障排查

### 常见问题

1. **配额不生效**
   - 检查数据库中配额是否正确设置
   - 检查时间窗口是否正确重置
   - 查看配额使用日志

2. **配额总是超限**
   - 检查配额限制是否设置过低
   - 查看是否有异常高频请求
   - 考虑调整配额设置

3. **Token API 无法设置配额**
   - 检查 Token 是否有足够权限
   - 检查用户角色是否允许
   - 查看错误消息

## 未来扩展

1. 支持更细粒度的配额类型（如按功能模块）
2. 支持配额自动充值
3. 支持配额过期时间
4. 支持配额转移功能
5. 支持配额使用分析和报表
