# 定时训练功能文档

## 概述

定时训练功能允许用户配置自动化的训练任务，支持全量训练和增量训练两种模式。该功能可以按照指定的时间规则（一次性、间隔执行、Cron表达式）自动触发训练，无需人工干预。

## 功能特性

### 触发方式

1. **一次性执行（Once）**
   - 在指定的时间点执行一次训练任务
   - 适用于需要在特定时间点执行的训练

2. **间隔执行（Interval）**
   - 按照固定的间隔时间（秒）重复执行训练任务
   - 例如：每小时执行一次（3600秒）

3. **Cron表达式（Cron）**
   - 使用Cron表达式定义复杂的执行时间规则
   - 支持标准5段Cron格式：分 时 日 月 周
   - 例如：`0 2 * * *` 表示每天凌晨2点执行

### 训练模式

1. **全量训练（Full Training）**
   - 使用所有已处理的样本进行完整训练
   - 适用于需要重新训练模型的场景
   - 可以通过`force_retrain`参数强制重新训练

2. **增量训练（Incremental Training）**
   - 只使用自上次训练后新增的样本进行训练
   - 适用于持续更新的场景
   - 更高效，训练时间更短

### 其他特性

- **学校级别训练**：可以为特定学校配置训练任务，或配置全校范围的训练
- **任务状态管理**：支持暂停、恢复、删除定时任务
- **执行统计**：记录每次执行的详细信息，包括成功/失败次数
- **执行历史**：查看任务的完整执行历史记录
- **权限控制**：系统管理员和学校管理员可以创建和管理定时任务

## 架构设计

### 数据库模型

#### ScheduledTask（定时任务表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | Text | 任务名称 |
| description | Text | 任务描述 |
| status | Enum | 任务状态（active/paused/completed/failed） |
| trigger_type | Enum | 触发器类型（once/interval/cron） |
| interval_seconds | Integer | 间隔秒数（interval触发器） |
| cron_expression | Text | Cron表达式（cron触发器） |
| run_at | DateTime | 执行时间（once触发器） |
| training_mode | Text | 训练模式（full/incremental） |
| school_id | Integer | 学校ID（可选，为空表示全校） |
| force_retrain | Boolean | 是否强制重新训练 |
| last_run_at | DateTime | 最后执行时间 |
| next_run_at | DateTime | 下次执行时间 |
| total_runs | Integer | 总执行次数 |
| success_runs | Integer | 成功次数 |
| failed_runs | Integer | 失败次数 |
| last_error | Text | 最后一次错误信息 |
| created_by | Integer | 创建者ID |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### ScheduledTaskExecution（定时任务执行记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| scheduled_task_id | Integer | 定时任务ID |
| training_job_id | Integer | 关联的训练任务ID |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |
| status | Text | 执行状态 |
| output | Text | 执行输出 |
| error_message | Text | 错误信息 |

### 任务调度器（APScheduler）

使用`APScheduler`库实现任务调度：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
```

调度器特性：
- 异步执行，不阻塞主线程
- 支持内存任务存储（可通过配置改为持久化存储）
- 每个任务最多同时运行1个实例
- 支持任务错失执行后的宽容时间（300秒）
- 应用启动时自动加载激活的任务

## API接口

### 后端API端点

#### 1. 创建定时任务

```http
POST /api/scheduled-tasks
```

请求体：
```json
{
  "name": "每天凌晨全量训练",
  "description": "每天凌晨2点执行全量训练",
  "trigger_type": "cron",
  "cron_expression": "0 2 * * *",
  "training_mode": "full",
  "school_id": null,
  "force_retrain": false
}
```

#### 2. 列出定时任务

```http
GET /api/scheduled-tasks?status=active&training_mode=full
```

查询参数：
- `status`: 按状态筛选（active/paused/completed/failed）
- `training_mode`: 按训练模式筛选（full/incremental）
- `school_id`: 按学校ID筛选
- `skip`: 跳过记录数（分页）
- `limit`: 限制返回记录数（分页）

#### 3. 获取定时任务详情

```http
GET /api/scheduled-tasks/{task_id}
```

#### 4. 更新定时任务

```http
PUT /api/scheduled-tasks/{task_id}
```

请求体：所有字段均为可选

#### 5. 删除定时任务

```http
DELETE /api/scheduled-tasks/{task_id}
```

#### 6. 暂停定时任务

```http
POST /api/scheduled-tasks/{task_id}/pause
```

#### 7. 恢复定时任务

```http
POST /api/scheduled-tasks/{task_id}/resume
```

#### 8. 查看任务执行历史

```http
GET /api/scheduled-tasks/{task_id}/executions
```

## 前端界面

### 定时任务管理页面

路径：`/scheduled-tasks`

功能：
- 任务列表展示（支持状态、模式筛选）
- 创建/编辑/删除任务
- 暂停/恢复任务
- 查看执行历史
- 任务统计仪表盘

### 主要组件

1. **任务统计卡片**
   - 活跃任务数
   - 暂停任务数
   - 总执行次数
   - 成功次数

2. **任务列表表格**
   - 任务名称、描述、状态
   - 触发方式、训练模式
   - 执行统计
   - 操作按钮（编辑、暂停/恢复、删除、查看历史）

3. **创建/编辑任务表单**
   - 任务名称、描述
   - 触发方式选择（一次性/间隔/Cron）
   - 触发器配置（根据触发方式动态显示）
   - 训练模式选择
   - 学校选择（可选）
   - 强制重新训练开关

4. **执行历史时间线**
   - 显示每次执行的详细信息
   - 执行状态、开始/完成时间
   - 错误信息（如有）

## CLI命令行工具

### 基本用法

```bash
python scripts/cli/scheduled_tasks.py <command> [options]
```

### 可用命令

#### 1. 列出所有定时任务

```bash
python scripts/cli/scheduled_tasks.py list
python scripts/cli/scheduled_tasks.py list --status active
python scripts/cli/scheduled_tasks.py list --training-mode full
```

#### 2. 创建定时任务

```bash
# 一次性执行
python scripts/cli/scheduled_tasks.py create \
  --name "测试任务" \
  --trigger-type once \
  --run-at "2024-02-01T14:30:00" \
  --training-mode full

# 间隔执行（每小时）
python scripts/cli/scheduled_tasks.py create \
  --name "每小时增量训练" \
  --trigger-type interval \
  --interval 3600 \
  --training-mode incremental

# Cron表达式（每天凌晨2点）
python scripts/cli/scheduled_tasks.py create \
  --name "每天凌晨全量训练" \
  --trigger-type cron \
  --cron "0 2 * * *" \
  --training-mode full \
  --school-id 1
```

#### 3. 更新定时任务

```bash
python scripts/cli/scheduled_tasks.py update \
  --id 1 \
  --name "新任务名称" \
  --status paused
```

#### 4. 删除定时任务

```bash
python scripts/cli/scheduled_tasks.py delete --id 1
```

#### 5. 暂停定时任务

```bash
python scripts/cli/scheduled_tasks.py pause --id 1
```

#### 6. 恢复定时任务

```bash
python scripts/cli/scheduled_tasks.py resume --id 1
```

#### 7. 显示任务详情

```bash
python scripts/cli/scheduled_tasks.py show --id 1
```

#### 8. 查看任务执行历史

```bash
python scripts/cli/scheduled_tasks.py history --id 1
python scripts/cli/scheduled_tasks.py history --id 1 --limit 50
```

## 使用示例

### 场景1：每天凌晨执行全量训练

使用CLI：
```bash
python scripts/cli/scheduled_tasks.py create \
  --name "每天凌晨全量训练" \
  --description "每天凌晨2点对全校数据进行全量训练" \
  --trigger-type cron \
  --cron "0 2 * * *" \
  --training-mode full
```

使用前端：
1. 进入"定时训练"页面
2. 点击"创建任务"
3. 填写表单：
   - 任务名称：每天凌晨全量训练
   - 触发方式：Cron表达式
   - Cron表达式：0 2 * * *
   - 训练模式：全量训练
4. 点击确定

### 场景2：每小时执行增量训练

使用CLI：
```bash
python scripts/cli/scheduled_tasks.py create \
  --name "每小时增量训练" \
  --trigger-type interval \
  --interval 3600 \
  --training-mode incremental
```

### 场景3：指定学校的定时训练

使用CLI：
```bash
python scripts/cli/scheduled_tasks.py create \
  --name "学校1每小时训练" \
  --trigger-type interval \
  --interval 3600 \
  --training-mode full \
  --school-id 1
```

## 注意事项

1. **数据库迁移**
   - 首次使用需要执行数据库迁移：
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **调度器启动**
   - 调度器会在后端应用启动时自动启动
   - 启动时会自动加载所有状态为"active"的任务

3. **Cron表达式格式**
   - 使用5段标准Cron格式：分 时 日 月 周
   - 示例：
     - `0 2 * * *` - 每天凌晨2点
     - `0 */6 * * *` - 每6小时
     - `0 9-18 * * 1-5` - 工作日9点到18点每小时

4. **增量训练条件**
   - 增量训练需要存在最新的模型版本
   - 只训练模型创建后的新增样本
   - 如果没有新增样本，任务会失败

5. **权限控制**
   - 系统管理员：可以管理所有任务
   - 学校管理员：只能管理本校的任务
   - 教师：可以查看任务，不能创建/编辑

6. **任务执行**
   - 每个任务同一时间最多运行一个实例
   - 如果前一次任务还在运行，新的执行会被跳过
   - 执行记录会保存到数据库，可随时查看

## 故障排查

### 任务未按时执行

1. 检查后端服务是否正常运行
2. 查看后端日志是否有调度器启动信息
3. 检查任务状态是否为"active"
4. 查看任务的"下次执行时间"是否正确

### 训练任务失败

1. 查看任务的执行历史，找到失败记录
2. 查看错误信息
3. 检查：
   - 样本数量是否足够（至少3个已处理样本）
   - 推理服务是否正常运行
   - 数据库连接是否正常

### Cron表达式无效

1. 确保使用5段格式：分 时 日 月 周
2. 使用通配符`*`表示所有值
3. 使用`*/n`表示间隔（例如`*/5`表示每5个单位）

## 扩展功能

未来可以考虑的扩展：

1. **持久化任务存储**：使用数据库存储调度器任务，支持分布式部署
2. **邮件/消息通知**：任务执行成功/失败时发送通知
3. **任务依赖**：支持任务之间的依赖关系
4. **更复杂的触发器**：支持日历触发器等
5. **任务超时控制**：设置任务最大执行时间
6. **重试机制**：失败任务自动重试

## 相关文件

### 后端
- `backend/app/models/scheduled_task.py` - 数据库模型
- `backend/app/api/scheduled_tasks.py` - API端点
- `backend/app/services/task_scheduler.py` - 任务调度器服务
- `backend/app/main.py` - 应用入口（调度器启动）

### 前端
- `frontend/src/pages/ScheduledTasks.tsx` - 定时任务管理页面
- `frontend/src/components/Layout.tsx` - 导航菜单更新

### CLI
- `scripts/cli/scheduled_tasks.py` - 命令行工具

### 数据库
- `backend/alembic/versions/` - 数据库迁移文件
