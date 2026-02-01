# 自动训练适配器 (Auto Training Adapter)

## 概述

自动训练适配器是一个智能模块，能够自动检测数据变化，决定训练策略，并动态调整超参数，实现深度模型的自动适配。该功能旨在减少人工干预，提高训练效率，并确保模型性能。

## 核心功能

### 1. 自动数据变化检测

自动分析数据库中的样本变化，检测以下类型的变化：

- **新用户 (NEW_USERS)**: 检测到新增用户
- **新样本 (NEW_SAMPLES)**: 检测到现有用户的新样本
- **样本移除 (SAMPLE_REMOVED)**: 检测到样本被删除
- **微小变化 (MINOR_CHANGE)**: 数据变化未达到训练阈值

**实现位置**: `inference_service/training/auto_adapter.py:107`

### 2. 智能训练策略选择

根据数据变化类型和数据特征，自动选择最优训练策略：

| 策略 | 适用场景 | 优点 |
|------|---------|------|
| **全量重训练 (FULL_RETRAIN)** | 新用户、样本移除、样本数量较少(≤1000) | 特征学习更充分，准确率更高 |
| **增量微调 (INCREMENTAL_FINE_TUNE)** | 新样本且样本数量较多(>1000) | 训练速度快，节省资源 |
| **无需训练 (NO_TRAINING)** | 数据变化未达到阈值 | 避免不必要的训练 |

**实现位置**: `inference_service/training/auto_adapter.py:182`

### 3. 动态超参数调整

根据数据特征和训练策略，自动计算最优超参数：

#### 全量重训练超参数
```python
{
    "batch_size": min(8, max(2, total_samples // 100)),  # 2-8
    "num_epochs": min(30, max(10, 20 - total_samples // 100)),  # 10-30
    "learning_rate": 0.001,
    "use_imagenet_pretrained": False  # 禁用ImageNet预训练
}
```

#### 增量微调超参数
```python
{
    "batch_size": min(8, max(2, total_samples // 50)),  # 2-8
    "num_epochs": min(10, max(5, 8 - total_samples // 200)),  # 5-10
    "learning_rate": 0.0001,  # 更小的学习率
    "freeze_backbone": True,  # 冻结骨干网络
}
```

**实现位置**: `inference_service/training/auto_adapter.py:227`

### 4. 训练结果自动评估

训练完成后，自动评估结果并决定是否接受新模型：

**评估标准**:
- 损失值不超过 10.0
- 验证准确率不低于 50%
- 与之前模型对比，准确率下降不超过 5%

如果未通过评估，自动回滚到之前的模型。

**实现位置**: `inference_service/training/auto_adapter.py:283`

## API 接口

### 1. 获取训练建议

获取当前数据的训练建议，包括推荐策略和原因。

**请求**:
```http
GET /api/training/recommendation
```

**响应**:
```json
{
  "should_train": true,
  "strategy": "full_retrain",
  "reason": "检测到新用户，需要全量训练以学习新特征",
  "change_type": "new_users",
  "change_ratio": 0.25,
  "priority": 10,
  "error_message": ""
}
```

**字段说明**:
- `should_train`: 是否应该训练
- `strategy`: 推荐策略 (full_retrain, incremental_fine_tune, no_training)
- `reason`: 原因说明
- `change_type`: 数据变化类型
- `change_ratio`: 数据变化比例 (0-1)
- `priority`: 优先级 (1-10, 10为最高)

### 2. 启动训练

启动训练任务，自动使用适配器建议的策略。

**请求**:
```http
POST /api/training
Content-Type: application/json

{
  "force_retrain": false
}
```

**响应**:
```json
{
  "id": 1,
  "status": "running",
  "progress": 0.0,
  "model_version_id": 1735672800,
  "started_at": "2026-01-31T10:00:00Z",
  "error_message": null
}
```

## 配置

### 适配器配置

配置文件路径: `inference_service/models/adapter_config.json`

**默认配置**:
```json
{
  "min_samples_per_user": 2,
  "training_threshold": 0.3,
  "max_samples_for_full_retrain": 1000,
  "auto_train_enabled": true,
  "max_history_size": 10,
  "strategy_weights": {
    "full_retrain": 1.0,
    "incremental_fine_tune": 0.7,
    "no_training": 0.0
  }
}
```

**配置说明**:
- `min_samples_per_user`: 每用户最小样本数
- `training_threshold`: 触发训练的数据变化比例阈值 (0-1)
- `max_samples_for_full_retrain`: 触发全量重训练的最大样本数
- `auto_train_enabled`: 是否启用自动训练
- `max_history_size`: 保留的历史训练记录数量

## 使用示例

### 示例 1: 获取训练建议

```bash
curl -X GET http://localhost:8000/api/training/recommendation \
  -H "Authorization: Bearer <token>"
```

**场景**: 首次训练，系统检测到 3 个用户，每个用户 5 个样本。

**响应**:
```json
{
  "should_train": true,
  "strategy": "full_retrain",
  "reason": "首次训练",
  "change_type": "new_users",
  "change_ratio": 1.0,
  "priority": 10
}
```

### 示例 2: 添加新样本后获取建议

**场景**: 添加 2 个用户的新样本（每个用户 3 个样本），总共增加 6 个样本。

**响应**:
```json
{
  "should_train": true,
  "strategy": "full_retrain",
  "reason": "样本数量较少，使用全量训练以获得更好的特征",
  "change_type": "new_samples",
  "change_ratio": 0.25,
  "priority": 6
}
```

### 示例 3: 微小变化无需训练

**场景**: 添加 1 个用户的 1 个样本（总样本 100 个）。

**响应**:
```json
{
  "should_train": false,
  "strategy": "no_training",
  "reason": "数据变化未达到训练阈值",
  "change_type": "new_samples",
  "change_ratio": 0.01,
  "priority": 0
}
```

### 示例 4: 大规模数据使用增量微调

**场景**: 添加 500 个新样本（总样本 1500 个）。

**响应**:
```json
{
  "should_train": true,
  "strategy": "incremental_fine_tune",
  "reason": "样本数量较多，使用增量微调以提高效率",
  "change_type": "new_samples",
  "change_ratio": 0.33,
  "priority": 4
}
```

## 工作流程

### 自动训练流程

```
1. 用户上传样本 → 数据库
                     ↓
2. 系统检测数据变化 (AutoTrainingAdapter)
                     ↓
3. 分析数据特征
   - 样本数量
   - 用户数量
   - 样本分布
   - 变化类型/比例
                     ↓
4. 决定训练策略
   - 全量重训练
   - 增量微调
   - 无需训练
                     ↓
5. 计算超参数
   - batch_size
   - num_epochs
   - learning_rate
                     ↓
6. 执行训练 (Trainer)
   - 使用动态超参数
   - 记录训练指标
                     ↓
7. 评估训练结果
   - 损失值检查
   - 准确率检查
   - 性能对比
                     ↓
8. 更新模型状态
   - 保存模型
   - 更新特征库
   - 记录历史
```

## 训练指标

训练完成后，系统会记录以下指标：

| 指标 | 说明 | 计算方式 |
|------|------|---------|
| `loss` | 平均损失值 | 所有epoch损失的平均值 |
| `validation_accuracy` | 验证准确率 | 1.0 - 平均损失（简化估计） |
| `training_time` | 训练时间（秒） | 训练结束时间 - 开始时间 |
| `model_size` | 模型大小（MB） | 参数和缓冲区大小 |
| `total_samples` | 训练样本数 | 参与训练的样本总数 |
| `unique_users` | 用户数 | 参与训练的唯一用户数 |

**查看方式**:
```bash
curl -X GET http://localhost:8000/api/training \
  -H "Authorization: Bearer <token>"
```

响应中包含 `training_metrics` 字段。

## 故障排查

### 问题 1: 自动适配器未生效

**症状**: 训练建议返回 `should_train: false` 但实际需要训练。

**解决方法**:
1. 检查配置文件 `adapter_config.json` 中的 `training_threshold` 值
2. 降低阈值，例如从 0.3 降到 0.2
3. 检查样本状态是否为 `PROCESSED`

### 问题 2: 训练评估未通过

**症状**: 训练完成后报错 "训练评估未通过: 准确率下降超过5%"

**解决方法**:
1. 使用 `force_retrain: true` 强制重训练
2. 检查数据质量和标注是否正确
3. 增加样本数量以提高模型性能

### 问题 3: PCA 维度不匹配

**症状**: 训练时报错 "PCA维度不匹配"

**解决方法**:
1. 删除旧的 PCA 模型: `rm inference_service/models/pca.pkl`
2. 重新训练

## 最佳实践

### 1. 定期获取训练建议

建议在每次添加样本后，先获取训练建议，再决定是否训练：

```bash
# 获取建议
curl -X GET http://localhost:8000/api/training/recommendation \
  -H "Authorization: Bearer <token>"

# 如果 should_train 为 true，再启动训练
curl -X POST http://localhost:8000/api/training \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"force_retrain": false}'
```

### 2. 监控训练进度

使用轮询方式监控训练进度：

```bash
while true; do
  curl -X GET http://localhost:8000/api/training \
    -H "Authorization: Bearer <token>" \
    | jq '.[] | {status, progress}'
  sleep 5
done
```

### 3. 根据业务调整阈值

根据实际业务需求调整配置：

- **高精度场景**: 降低 `training_threshold` 到 0.2，增加训练频率
- **低延迟场景**: 提高 `training_threshold` 到 0.5，减少训练频率

### 4. 定期检查训练历史

查看训练历史，了解模型演进：

```bash
cat inference_service/models/adapter_state.json | jq '.training_history'
```

## 技术架构

### 模块依赖关系

```
AutoTrainingAdapter
    ├── 数据变化检测 (detect_data_changes)
    ├── 数据特征分析 (analyze_data_characteristics)
    ├── 策略决策 (decide_training_strategy)
    ├── 超参数计算 (_calculate_hyperparameters)
    ├── 结果评估 (evaluate_training_result)
    └── 状态管理 (update_training_state)

Trainer
    ├── 集成 AutoTrainingAdapter
    ├── 执行训练 (train)
    ├── 提取特征 (_update_user_features)
    └── 获取建议 (get_training_recommendation)

gRPC Server
    ├── HandwritingInferenceServicer
    │   ├── GetTrainingRecommendation
    │   └── TrainModel
    └── 自动适配器集成

Backend API
    ├── GET /api/training/recommendation
    └── POST /api/training
```

### 文件结构

```
inference_service/
├── training/
│   ├── auto_adapter.py          # 自动适配器核心逻辑
│   └── trainer.py               # 训练器（已集成自动适配）
├── grpc_server/
│   └── server.py                # gRPC服务（新增方法）
├── models/
│   ├── adapter_config.json       # 适配器配置
│   ├── adapter_state.json        # 适配器状态
│   └── pca.pkl                 # PCA模型
└── core/
    └── config.py               # 全局配置

backend/
├── app/
│   ├── api/
│   │   └── training.py         # 训练API（新增端点）
│   └── services/
│       └── inference_client.py  # gRPC客户端（新增方法）

shared/
└── proto/
    └── handwriting_inference.proto  # protobuf定义（新增消息）
```

## 更新日志

### v1.0.0 (2026-01-31)

**新增功能**:
- ✅ 自动数据变化检测
- ✅ 智能训练策略选择
- ✅ 动态超参数调整
- ✅ 训练结果自动评估
- ✅ 训练建议 API
- ✅ 训练历史记录

**性能优化**:
- ✅ 增量微调策略减少训练时间
- ✅ 动态 batch_size 优化内存使用
- ✅ 自动评估避免性能退化

## 相关文档

- [训练服务文档](./DEVELOPMENT.md)
- [识别修复文档](./RECOGNITION_FIX.md)
- [实现检查文档](./IMPLEMENTATION_CHECK.md)
