# 字迹识别系统

一个基于Few-shot Learning的字迹识别系统，用于识别作业上的字迹归属。

> 📖 **详细开发指南**: 请参阅 [DEVELOPMENT.md](./docs/DEVELOPMENT.md) 获取完整的开发文档。

## 项目结构

- `backend/` - Web后端（FastAPI）
- `inference_service/` - 独立推理服务（gRPC + PyTorch）
- `frontend/` - React前端
- `desktop/` - Windows桌面应用（PyQt6）
- `shared/` - 共享代码（Protobuf定义）
- `docker/` - Docker部署配置

## 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL
- 推理服务：PyTorch + gRPC
- 前端：React + TypeScript + Ant Design
- 桌面：PyQt6
- 算法：Siamese Network + Few-shot Learning

## 快速开始

### 1. 数据库设置

```bash
# 创建MySQL数据库
mysql -u root -p
CREATE DATABASE handwriting_recognition CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 后端设置

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 配置 .env 文件
alembic upgrade head
uvicorn app.main:app --reload
```

**注意**: 如果遇到 `libstdc++.so.6` 或 Nix Python 相关的错误，可以使用以下解决方案：

1. **使用修复脚本**（推荐）:
   ```bash
   cd backend
   ./fix_venv.sh  # 使用系统Python重新创建虚拟环境
   ```

2. **使用启动脚本**:
   ```bash
   cd backend
   ./run_server.sh  # 自动检测并使用系统Python
   ```

3. **手动使用系统Python**:
   ```bash
   cd backend
   ./run_with_system_python.sh
   ```

### 3. 推理服务

```bash
cd inference_service
pip install -r requirements.txt
cp .env.example .env
# 配置 .env 文件
python grpc_server/server.py
```

### 4. 前端

```bash
cd frontend
npm install
npm start
```

## 推荐服务器配置（部署建议）

本项目包含 **FastAPI 后端 + 推理服务（PyTorch + OpenCV + gRPC）+ MySQL + Redis + 前端静态站点**。
其中最吃资源的是 **推理服务（深度模型推理）**，因此服务器配置主要取决于是否使用 GPU、以及预期并发量。

### 1) 入门 / 开发 / 小规模试运行（CPU 推理）

适合：内网试用、并发很低（<5 QPS）、对时延要求不极致。

- **CPU**：8 核（x86_64）
- **内存**：16–32 GB（建议 32GB）
- **磁盘**：200GB SSD（镜像/上传样本/模型/日志）
- **GPU**：不需要
- **系统**：Ubuntu 22.04 LTS（推荐）

部署方式建议：
- 单机 Docker Compose 跑全套（MySQL/Redis/backend/inference/frontend/nginx）

### 2) 推荐生产（GPU 推理，中小规模）

适合：需要较好的识别速度、并发中等（5–50 QPS，视模型复杂度而定）。

- **CPU**：16 核
- **内存**：64 GB
- **磁盘**：500GB–1TB NVMe SSD
- **GPU**：1 张 NVIDIA（建议 **>= 16GB 显存**）
  - 常见选择：T4 16GB、A10 24GB、L4 24GB、A4000/A5000 等
- **网络**：千兆网卡

部署方式建议：
- 推理服务单独部署到 GPU 机器
- 后端 + MySQL + Redis 可同机或拆分（根据数据量/并发）
- 前端静态文件由 Nginx 托管

### 3) 可扩展生产（高并发 / 高可用）

适合：并发较高、需要横向扩容与稳定性。

- **API（FastAPI）**：2 台起（或 K8s 多副本），每台 8–16 核 / 16–32GB
- **推理服务**：多台 GPU 服务器（按吞吐扩容）
- **MySQL**：建议单独机器（主从/高可用），16 核 / 64GB / NVMe
- **Redis**：建议单独机器或哨兵/集群
- **对象存储**：建议将 `uploads/` 放 OSS/S3/MinIO，避免本地盘扩容困难
- **负载均衡**：Nginx/Ingress + 健康检查

### 关键注意事项

- **推理服务依赖较重**：PyTorch/OpenCV/PaddleOCR 建议容器化并固定版本。
- **模型与特征库**：
  - 模型权重：`inference_service/models/`（无 `.pth` 时会尝试使用 ImageNet 预训练作为兜底）。
  - 特征库：推理服务会从 DB 表 `user_features` 读取用户特征向量（没有特征库将无法返回有效 Top-K）。
- **GPU 部署**：Docker 场景需要安装 NVIDIA 驱动与 nvidia-container-toolkit。

## Docker 快速部署

```bash
# 复制环境变量配置
cp .env.example .env

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

服务启动后访问：
- 前端: http://localhost:3000
- API文档: http://localhost:8000/docs

## 主要功能

### Web前端
- ✅ 用户认证（登录/注册/登出）
- ✅ 样本上传（支持拖拽）
- ✅ 样本管理（列表/画廊视图切换）
- ✅ 图片裁剪（手动标注手写区域）
- ✅ 字迹识别（上传图片识别归属）
- ✅ 训练管理（触发模型训练）

### 桌面端(PyQt6)
- ✅ 图片选择和拖拽上传
- ✅ 字迹识别
- ✅ 识别历史记录

### 推理服务
- ✅ 图像预处理（打印/手写分离、增强）
- ✅ 深度学习特征提取（Siamese Network）
- ✅ 传统特征提取（LBP、Gabor等）
- ✅ 特征融合与匹配
- ✅ 模型训练

## 用户角色

| 角色 | 权限 |
|------|------|
| 系统管理员 | 管理所有学校、用户、系统配置 |
| 学校管理员 | 管理本校教师和学生 |
| 教师 | 上传样本、训练模型、识别作业 |
| 学生 | 查看自己的样本和识别记录 |

## 文档

- [开发指南](./docs/DEVELOPMENT.md) - 详细的开发环境搭建和规范
- [实现检查](./docs/IMPLEMENTATION_CHECK.md) - 功能完成度检查报告

## License

MIT License
