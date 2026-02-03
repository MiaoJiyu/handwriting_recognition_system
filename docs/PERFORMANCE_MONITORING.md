# 性能监控与日志分析系统

本文档介绍字迹识别系统的性能监控和日志分析功能。

## 概述

系统实现了全面的性能监控和日志收集分析功能，包括：

- **性能指标收集**: 自动收集请求响应时间、错误率、系统资源使用等指标
- **结构化日志**: 支持JSON格式的结构化日志，便于日志分析
- **日志轮转**: 自动日志文件轮转和清理
- **监控仪表板**: 前端可视化的监控仪表板
- **日志查询**: 支持按级别、时间范围、关键词查询日志

## 架构

### 后端监控组件

```
backend/app/
├── middleware/
│   └── performance.py          # 性能监控中间件
├── api/
│   └── monitoring.py           # 监控API端点
└── utils/
    └── structured_logger.py    # 结构化日志工具
```

### 推理服务监控组件

```
inference_service/utils/
└── performance_monitor.py      # 推理服务性能监控
```

### 前端监控组件

```
frontend/src/
├── pages/
│   └── MonitoringDashboard.tsx # 监控仪表板页面
├── services/
│   └── monitoring.ts           # 监控API客户端
└── pages/
    └── Monitoring.css          # 监控页面样式
```

## 核心功能

### 1. 性能指标收集

#### 自动收集的指标

- **HTTP请求指标**
  - `http_request_duration_ms`: HTTP请求响应时间
  - `http_requests_total`: 请求总数
  - `http_errors_total`: 错误总数

- **系统资源指标**
  - CPU使用率
  - 内存使用情况
  - 磁盘使用情况
  - 进程状态

- **推理服务指标**
  - `recognize_duration_ms`: 识别耗时
  - `batch_recognize_duration_ms`: 批量识别耗时
  - `train_duration_ms`: 训练耗时
  - `feature_extraction_duration_ms`: 特征提取耗时

#### 指标统计

支持多种统计方式：

- **平均值**: 所有指标的平均值
- **百分位数**: P95、P99百分位数
- **最小值/最大值**: 指标的范围
- **计数**: 指标出现的次数

### 2. 结构化日志

#### 日志级别

- **DEBUG**: 调试信息
- **INFO**: 一般信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

#### 日志格式

支持两种日志格式：

**文本格式**:
```
2026-02-02 14:30:45 - app.api.recognition - INFO - recognize:123 - 识别请求处理完成
```

**JSON格式**:
```json
{
  "timestamp": "2026-02-02T14:30:45.123456",
  "level": "INFO",
  "module": "app.api.recognition",
  "function": "recognize",
  "line": 123,
  "message": "识别请求处理完成",
  "request_id": "1234567890_12345678",
  "duration_ms": 45.67,
  "method": "POST",
  "path": "/api/recognition"
}
```

#### 日志文件

系统会创建多个日志文件：

- `backend.log`: 所有日志
- `backend_error.log`: ERROR及以上级别日志
- `backend_slow.log`: 慢请求日志（耗时>1秒）

### 3. 监控API端点

#### 获取性能指标

```
GET /api/monitoring/metrics
```

**参数**:
- `metric_name`: 指标名称（可选）
- `minutes`: 时间范围（分钟），默认5分钟
- `format_type`: 格式类型（summary/raw），默认summary

**示例**:
```bash
# 获取所有指标汇总
curl http://localhost:8000/api/monitoring/metrics

# 获取特定指标
curl http://localhost:8000/api/monitoring/metrics?metric_name=http_request_duration_ms&minutes=10

# 获取原始数据
curl http://localhost:8000/api/monitoring/metrics?metric_name=http_request_duration_ms&format_type=raw
```

#### 系统健康检查

```
GET /api/monitoring/health
```

**参数**:
- `detailed`: 是否返回详细信息，默认false

**示例**:
```bash
# 简单健康检查
curl http://localhost:8000/api/monitoring/health

# 详细健康检查
curl http://localhost:8000/api/monitoring/health?detailed=true
```

#### 查询日志

```
GET /api/monitoring/logs
```

**参数**:
- `level`: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- `start_time`: 开始时间（ISO格式）
- `end_time`: 结束时间（ISO格式）
- `limit`: 返回条数限制，默认100
- `keyword`: 关键词搜索

**示例**:
```bash
# 查询ERROR级别日志
curl http://localhost:8000/api/monitoring/logs?level=ERROR&limit=50

# 关键词搜索
curl http://localhost:8000/api/monitoring/logs?keyword=识别失败&limit=20
```

#### 获取系统统计

```
GET /api/monitoring/stats
```

**示例**:
```bash
curl http://localhost:8000/api/monitoring/stats
```

**返回数据**:
```json
{
  "success": true,
  "data": {
    "users": {"total": 100},
    "samples": {"total": 5000},
    "recognition": {"total": 10000, "recent_24h": 500},
    "training": {"total": 20}
  }
}
```

#### 清理旧指标

```
POST /api/monitoring/clear-old-metrics
```

**参数**:
- `hours`: 清理多少小时之前的数据，默认24小时

**示例**:
```bash
curl -X POST http://localhost:8000/api/monitoring/clear-old-metrics?hours=24
```

## 前端监控仪表板

### 访问监控仪表板

启动前端服务后，访问：
```
http://localhost:5173/monitoring
```

### 仪表板功能

#### 1. 系统健康状态

- **CPU使用率**: 实时显示CPU使用百分比
- **内存使用率**: 显示内存占用情况
- **磁盘使用率**: 显示磁盘空间使用情况
- **系统状态**: 显示系统健康状态
- **进程信息**: 显示进程ID、内存占用、运行时间等

#### 2. 系统统计

- **用户总数**: 系统注册用户数
- **样本总数**: 上传的样本数量
- **识别总数**: 历史识别总次数
- **最近24小时识别**: 最近一天的识别次数

#### 3. 性能指标

- **平均响应时间**: 请求的平均响应时间
- **P95响应时间**: 95%的请求响应时间
- **P99响应时间**: 99%的请求响应时间
- **请求计数**: 总请求数和错误数

#### 4. 日志查询

- **日志级别过滤**: 按级别过滤日志
- **关键词搜索**: 搜索包含特定关键词的日志
- **显示数量**: 设置返回的日志条数
- **日志表格**: 显示详细的日志信息

### 使用示例

```typescript
// 获取性能指标
import { getPerformanceMetrics } from '@/services/monitoring';

const metrics = await getPerformanceMetrics('http_request_duration_ms', 5);
console.log('平均响应时间:', metrics.data.average);

// 获取系统健康状态
import { getHealthStatus } from '@/services/monitoring';

const health = await getHealthStatus(true);
console.log('CPU使用率:', health.data.system.cpu_percent);

// 查询日志
import { queryLogs } from '@/services/monitoring';

const logs = await queryLogs({
  level: 'ERROR',
  keyword: '识别失败',
  limit: 100
});
console.log('错误日志:', logs.data);
```

## 推理服务性能监控

### 使用装饰器监控函数

```python
from inference_service.utils.performance_monitor import monitor_inference

@monitor_inference('recognize')
async def recognize(image_path: str, top_k: int = 5):
    # 识别逻辑
    pass
```

### 使用上下文管理器监控操作

```python
from inference_service.utils.performance_monitor import monitor_operation

with monitor_operation('feature_extraction', logger):
    features = extract_features(image)
```

### 手动记录性能日志

```python
from inference_service.utils.performance_monitor import log_performance

start_time = time.time()
# 执行操作
duration_ms = (time.time() - start_time) * 1000

log_performance(
    logger,
    'custom_operation',
    duration_ms,
    {'user_id': user_id, 'image_count': len(images)}
)
```

## 配置

### 后端配置

在 `backend/.env` 中添加：

```bash
# 日志配置
LOG_DIR=./logs
LOG_LEVEL=INFO
LOG_ENABLE_JSON=true
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=10
```

### 前端配置

在 `frontend/src/App.tsx` 中添加监控路由：

```typescript
import MonitoringDashboard from './pages/MonitoringDashboard';

// 在路由配置中添加
<Route path="/monitoring" element={<ProtectedRoute><MonitoringDashboard /></ProtectedRoute>} />
```

## 最佳实践

### 1. 日志级别使用

- **DEBUG**: 开发和调试时使用
- **INFO**: 记录正常的业务流程
- **WARNING**: 记录潜在问题（如慢请求）
- **ERROR**: 记录需要关注的错误
- **CRITICAL**: 记录系统级别的严重错误

### 2. 性能监控

- 为关键路径添加性能监控
- 设置合理的性能阈值
- 定期分析性能指标，识别瓶颈
- 优化慢查询和慢操作

### 3. 日志管理

- 定期清理旧日志文件
- 使用日志轮转避免磁盘空间问题
- 配置合适的日志级别
- 在生产环境避免使用DEBUG级别

### 4. 监控告警

- 设置关键指标的告警阈值
- 定期检查系统健康状态
- 监控错误率和慢请求率
- 建立故障响应流程

## 故障排查

### 问题：日志文件过大

**原因**: 日志文件没有正确轮转

**解决方案**:
1. 检查 `LOG_MAX_BYTES` 和 `LOG_BACKUP_COUNT` 配置
2. 手动清理旧日志文件
3. 使用 `POST /api/monitoring/clear-old-metrics` 清理旧指标

### 问题：性能指标不准确

**原因**: 时间范围设置不当或指标收集器未正确初始化

**解决方案**:
1. 检查监控中间件是否正确加载
2. 调整 `minutes` 参数获取更准确的数据
3. 重启服务重新初始化指标收集器

### 问题：日志查询速度慢

**原因**: 日志文件过大或查询条件过于复杂

**解决方案**:
1. 增加 `limit` 参数限制返回条数
2. 使用关键词搜索缩小范围
3. 定期清理旧日志文件
4. 考虑使用日志聚合工具（如ELK Stack）

### 问题：系统资源监控不准确

**原因**: psutil库未正确安装或权限不足

**解决方案**:
1. 安装psutil: `pip install psutil>=5.9.6`
2. 检查系统权限
3. 使用简单健康检查（不使用 `detailed=true`）

## 扩展

### 集成Prometheus

可以轻松将监控数据导出到Prometheus：

```python
from prometheus_client import Counter, Histogram, start_http_server

# 定义指标
request_duration = Histogram('http_request_duration_ms', 'HTTP request duration')
request_count = Counter('http_requests_total', 'Total HTTP requests')

# 在中间件中记录
request_duration.observe(duration_ms)
request_count.inc()

# 启动Prometheus服务器
start_http_server(8001)
```

### 集成日志聚合

可以使用以下工具进行日志聚合和分析：

- **ELK Stack**: Elasticsearch + Logstash + Kibana
- **Loki**: Grafana Loki轻量级日志聚合
- **Graylog**: 开源日志管理平台

### 添加自定义指标

```python
from backend.middleware.performance import metrics_collector

# 记录自定义指标
metrics_collector.record_metric('custom_metric', value, {
    'tag1': 'value1',
    'tag2': 'value2'
})
```

## 依赖安装

### 后端依赖

```bash
cd backend
pip install psutil>=5.9.6
pip install python-json-logger>=2.0.7
pip install prometheus-client>=0.19.0
```

### 前端依赖

前端不需要额外的依赖，使用现有的Ant Design组件即可。

## 总结

性能监控和日志分析系统提供了：

1. **全面的性能指标收集**: 自动收集HTTP请求、系统资源、推理服务等性能指标
2. **结构化日志**: 支持JSON格式，便于日志分析和搜索
3. **可视化仪表板**: 前端提供直观的监控界面
4. **灵活的日志查询**: 支持多种过滤和搜索条件
5. **易于扩展**: 可以轻松集成到其他监控工具

通过这些功能，管理员可以：
- 实时监控系统健康状态
- 分析系统性能瓶颈
- 快速定位和解决问题
- 优化系统性能和用户体验
