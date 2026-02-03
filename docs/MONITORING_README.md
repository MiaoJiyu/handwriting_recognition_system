# 性能监控与日志分析系统 - 快速开始

## 安装依赖

### 后端依赖

```bash
cd backend
pip install psutil>=5.9.6
pip install python-json-logger>=2.0.7
pip install prometheus-client>=0.19.0
```

### 前端依赖

前端无需额外依赖，使用现有的Ant Design组件。

## 配置

### 后端配置

在 `backend/.env` 中添加以下配置：

```bash
# 日志配置
LOG_DIR=./logs
LOG_LEVEL=INFO
LOG_ENABLE_JSON=true
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=10
```

### 前端配置

在 `frontend/src/App.tsx` 的路由配置中添加监控路由：

```typescript
import MonitoringDashboard from './pages/MonitoringDashboard';

// 在路由配置中添加
<Route path="/monitoring" element={<ProtectedRoute><MonitoringDashboard /></ProtectedRoute>} />
```

## 启动服务

### 启动后端

```bash
cd backend
./run_server.sh
```

### 启动前端

```bash
cd frontend
npm run dev
```

## 测试监控功能

运行测试脚本：

```bash
python test_monitoring.py
```

这会：
1. 检查后端服务是否运行
2. 生成测试流量
3. 测试所有监控API端点

## 访问监控仪表板

启动前端后，访问：
```
http://localhost:5173/monitoring
```

## API端点

### 获取性能指标
```
GET /api/monitoring/metrics
```

### 系统健康检查
```
GET /api/monitoring/health?detailed=true
```

### 查询日志
```
GET /api/monitoring/logs?level=ERROR&limit=100
```

### 获取系统统计
```
GET /api/monitoring/stats
```

### 清理旧指标
```
POST /api/monitoring/clear-old-metrics?hours=24
```

## 日志文件

日志文件位于 `backend/logs/` 目录：

- `backend.log`: 所有日志
- `backend_error.log`: ERROR及以上级别
- `backend_slow.log`: 慢请求日志（>1秒）

## 监控仪表板功能

1. **系统健康状态**: CPU、内存、磁盘使用率
2. **系统统计**: 用户、样本、识别次数
3. **性能指标**: 响应时间、P95/P99百分位数
4. **日志查询**: 按级别、关键词搜索日志

## 推理服务监控

在推理服务中使用性能监控：

```python
from inference_service.utils.performance_monitor import monitor_inference, monitor_operation

# 使用装饰器
@monitor_inference('recognize')
async def recognize(image_path: str):
    # 识别逻辑
    pass

# 使用上下文管理器
with monitor_operation('feature_extraction', logger):
    features = extract_features(image)
```

## 故障排查

### 问题：监控API返回404

**解决方案**: 确保在 `backend/app/main.py` 中注册了监控路由：
```python
from .api import monitoring_router
app.include_router(monitoring_router)
```

### 问题：日志文件不存在

**解决方案**: 检查 `LOG_DIR` 配置，确保目录存在且有写入权限：
```bash
mkdir -p backend/logs
chmod 755 backend/logs
```

### 问题：性能指标为空

**解决方案**: 确保性能监控中间件已加载：
```python
from .middleware.performance import PerformanceMiddleware
app.add_middleware(PerformanceMiddleware)
```

## 更多信息

详细文档请参考：[docs/PERFORMANCE_MONITORING.md](./docs/PERFORMANCE_MONITORING.md)
