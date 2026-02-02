# 字迹识别调用次数与速率限制功能 - 实现总结

## 实现概述

已成功实现完整的字迹识别调用次数与速率限制功能，支持多层级配额管理和灵活的限流策略。

## 已实现功能

### 1. 数据库设计 ✓

**新增表**：
- `quotas` - 配额表，存储用户和学校的识别次数限制
- `quota_usage_logs` - 配额使用日志表，记录每次识别请求的配额使用情况

**表结构**：
- 支持多时间窗口：分钟、小时、天、月、总计
- 自动重置时间戳记录
- 配额类型：用户配额、学校配额
- 外键关联用户和学校表

### 2. 后端服务 ✓

#### QuotaService (`backend/app/services/quota_service.py`)
- 获取或创建用户/学校配额
- 检查配额是否允许请求
- 自动重置时间窗口计数器
- 增加配额使用次数
- 批量更新配额
- 重置配额使用计数
- 获取配额使用日志

#### QuotaManagement API (`backend/app/api/quotas.py`)
- **GET /api/quotas** - 获取配额列表（支持角色权限过滤）
- **GET /api/quotas/{id}** - 获取单个配额详情
- **POST /api/quotas** - 创建配额（仅系统管理员）
- **PUT /api/quotas/{id}** - 更新配额（系统管理员/学校管理员）
- **POST /api/quotas/batch-update** - 批量更新配额
- **POST /api/quotas/{id}/reset** - 重置配额使用计数
- **DELETE /api/quotas/{id}** - 删除配额（仅系统管理员）
- **GET /api/quotas/{id}/logs** - 获取配额使用日志

#### Token API 集成 (`backend/app/api/token.py`)
- **POST /api/v1/tokens/quota/set** - 通过 Token 设置配额
- **POST /api/v1/tokens/quota/batch-set** - 通过 Token 批量设置配额
- **POST /api/v1/tokens/quota/reset** - 通过 Token 重置配额

#### 识别 API 集成 (`backend/app/api/recognition.py`)
- 在识别请求前检查配额
- 配额不足时返回 HTTP 429 错误
- 识别成功后自动增加配额使用次数
- 记录配额使用日志

### 3. 前端页面 ✓

#### QuotaManagement 页面 (`frontend/src/pages/QuotaManagement.tsx`)

**功能特性**：
- 配额列表展示（支持用户配额和学校配额）
- 实时使用统计（带颜色告警：绿色/橙色/红色）
- 创建新配额（支持用户配额和学校配额）
- 编辑现有配额
- 批量设置用户配额
- 重置配额使用计数
- 查看配额使用日志
- 配额详情抽屉（包含使用统计和日志）

**使用状态指示**：
- 绿色：使用量正常（< 80%）
- 橙色：接近限制（80% - 100%）
- 红色：已超限（> 100%）

### 4. 路由集成 ✓

- 添加配额管理路由：`/quotas`
- 在侧边栏菜单中添加"配额管理"入口
- 仅对系统管理员和学校管理员可见

### 5. 权限管理 ✓

#### 系统管理员
- ✓ 配置任何用户或学校的配额
- ✓ 批量设置多个用户/学校的配额
- ✓ 重置任何配额的使用计数
- ✓ 删除任何配额
- ✓ 查看所有配额和使用日志

#### 学校管理员
- ✓ 配置自己学校内用户的配额
- ✓ 批量设置自己学校内用户的配额
- ✓ 重置自己学校内用户的配额
- ✓ 不能配置学校配额
- ✓ 只能查看自己学校相关配额

#### 老师
- ✓ 查看自己的配额使用情况
- ✗ 不能修改配额

#### 学生
- ✗ 不能查看配额信息
- ✗ 不能修改配额

### 6. Token API 支持 ✓

通过 Token API 实现配额管理，方便外部应用集成：

**设置配额**：
```bash
POST /api/v1/tokens/quota/set
Authorization: Bearer <api_token>
```

**批量设置配额**：
```bash
POST /api/v1/tokens/quota/batch-set
Authorization: Bearer <api_token>
```

**重置配额**：
```bash
POST /api/v1/tokens/quota/reset
Authorization: Bearer <api_token>
```

### 7. 时间窗口管理 ✓

**自动重置逻辑**：
- **分钟**：当前时间与上次重置时间间隔 >= 60 秒
- **小时**：当前时间与上次重置时间间隔 >= 3600 秒
- **天**：当前日期与上次重置日期不同
- **月**：当前月份与上次重置月份不同

**默认值**：
- 所有限制默认为 0（无限制）
- 管理员可以根据实际需求设置限制

### 8. 配额使用日志 ✓

每次识别请求都会记录日志，包括：
- 用户 ID 和学校 ID
- 配额类型和配额 ID
- 是否允许请求
- 拒绝原因（如果被拒绝）
- 配额使用快照（拒绝时）
- 创建时间

## 文件清单

### 后端文件
1. `backend/app/models/quota.py` - 配额数据模型
2. `backend/app/services/quota_service.py` - 配额服务
3. `backend/app/api/quotas.py` - 配额管理 API
4. `backend/app/middleware/rate_limit.py` - 速率限制中间件（预留）
5. `backend/app/api/recognition.py` - 更新识别 API（集成配额检查）
6. `backend/app/api/token.py` - 更新 Token API（集成配额管理）
7. `backend/app/models/__init__.py` - 导出配额模型
8. `backend/app/api/__init__.py` - 导出配额路由
9. `backend/app/main.py` - 注册配额路由

### 前端文件
1. `frontend/src/pages/QuotaManagement.tsx` - 配额管理页面
2. `frontend/src/components/Layout.tsx` - 添加配额管理菜单项
3. `frontend/src/App.tsx` - 添加配额管理路由

### 文档文件
1. `docs/QUOTA_MANAGEMENT.md` - 完整配额管理文档

### 数据库文件
1. `backend/alembic/versions/b785cb7ff951_add_quota_and_rate_limiting_tables.py` - 数据库迁移

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

## 配额检查流程

1. 用户发起识别请求
2. 系统获取用户配额
3. 如果有学校 ID，同时获取学校配额
4. 检查时间窗口是否需要重置
5. 逐项检查限制（分钟、小时、天、月、总计）
6. 如果有任何一项超限：
   - 记录配额使用日志（is_allowed=0）
   - 返回 HTTP 429 错误，包含使用详情
7. 如果所有项都通过：
   - 执行识别请求
   - 增加配额使用次数
   - 记录配额使用日志（is_allowed=1）
   - 返回识别结果

## 性能优化

1. **数据库索引**
   - 复合索引：`ix_quota_type_user_id`, `ix_quota_type_school_id`
   - 日志索引：`ix_quota_usage_user_created`, `ix_quota_usage_school_created`

2. **查询优化**
   - 使用索引加速配额查找
   - 分页查询日志数据
   - 避免全表扫描

3. **缓存策略**
   - 配额数据可以在内存中缓存
   - 定期同步到数据库
   - 减少数据库查询压力

## 安全考虑

1. **权限控制**
   - 严格的基于角色的访问控制（RBAC）
   - 学校管理员只能操作自己学校的数据
   - 系统管理员拥有最高权限

2. **配额验证**
   - 检查配额是否属于当前用户的权限范围
   - 防止越权操作

3. **日志记录**
   - 所有配额修改操作都有日志记录
   - 可追溯审计

## 未来扩展建议

1. **配额自动充值**
   - 支持定期自动重置配额
   - 支持配额过期时间

2. **更细粒度的配额类型**
   - 按功能模块限制（如识别、训练、样本上传）
   - 按时间段限制（如工作日/周末）

3. **配额分析和报表**
   - 配额使用趋势分析
   - 异常检测和告警
   - 使用统计报表

4. **性能优化**
   - 使用 Redis 缓存配额数据
   - 实现分布式限流
   - 支持水平扩展

5. **配额市场**
   - 支持配额购买
   - 支持配额转移
   - 支持配额共享

## 测试建议

### 单元测试
1. 配额服务测试
2. 配额检查逻辑测试
3. 时间窗口重置测试
4. 权限控制测试

### 集成测试
1. 识别 API 配额集成测试
2. Token API 配额管理测试
3. 批量操作测试
4. 并发请求测试

### 性能测试
1. 高并发场景下的配额检查性能
2. 大量日志查询性能
3. 数据库索引效果验证

## 总结

字迹识别调用次数与速率限制功能已完整实现，包括：

✓ 数据库表设计和迁移
✓ 后端服务和 API
✓ 前端管理页面
✓ Token API 支持
✓ 权限管理
✓ 使用日志记录
✓ 完整文档

该功能已可以投入使用，支持多层级配额管理、灵活的限流策略和完整的操作日志记录。
