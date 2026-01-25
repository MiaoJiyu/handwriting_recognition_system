# 字迹识别系统开发指南

本文档提供详细的开发环境搭建、架构说明、开发规范和部署指南。

## 目录

- [环境要求](#环境要求)
- [项目架构](#项目架构)
- [本地开发](#本地开发)
- [Docker部署](#docker部署)
- [API文档](#api文档)
- [开发规范](#开发规范)
- [测试指南](#测试指南)
- [常见问题](#常见问题)

---

## 环境要求

### 基础环境

| 软件 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.10+ | 后端、推理服务、桌面端 |
| Node.js | 18+ | 前端开发 |
| MySQL | 8.0+ | 主数据库 |
| Redis | 6.0+ | 缓存服务 |
| Docker | 20.0+ | 容器化部署（可选） |

### Python 依赖

```bash
# 后端核心依赖
fastapi>=0.104.0
sqlalchemy>=2.0.0
pymysql>=1.1.0
pydantic>=2.0.0
python-jose>=3.3.0
passlib>=1.7.4

# 推理服务核心依赖
torch>=2.0.0
torchvision>=0.15.0
opencv-python>=4.8.0
scikit-learn>=1.3.0
grpcio>=1.59.0
```

### Node.js 依赖

```bash
# 前端核心依赖
react@^18.2.0
typescript@^5.3.0
antd@^5.12.0
axios@^1.6.0
@tanstack/react-query@^5.12.0
```

---

## 项目架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端层                                │
├─────────────────┬───────────────────┬───────────────────────┤
│   Web前端       │   桌面端(PyQt6)    │    移动端(未来)        │
│   (React)       │                   │                       │
└────────┬────────┴─────────┬─────────┴───────────────────────┘
         │                  │
         │ HTTP/REST        │ gRPC
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│   API网关       │  │   推理服务       │
│   (FastAPI)     │◄─┤   (gRPC)        │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ├────────────────────┤
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│    MySQL        │  │    Redis        │
│    数据库       │  │    缓存         │
└─────────────────┘  └─────────────────┘
```

### 目录结构详解

```
handwriting_recognition_system/
├── backend/                    # FastAPI后端服务
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   ├── auth.py        # 认证接口
│   │   │   ├── users.py       # 用户管理
│   │   │   ├── samples.py     # 样本管理
│   │   │   ├── recognition.py # 识别接口
│   │   │   ├── training.py    # 训练接口
│   │   │   └── schools.py     # 学校管理
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   └── database.py    # 数据库连接
│   │   ├── models/            # SQLAlchemy模型
│   │   ├── services/          # 业务服务
│   │   └── utils/             # 工具函数
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt
│
├── inference_service/          # 推理服务
│   ├── preprocessing/         # 图像预处理
│   │   ├── image_processor.py # 基础处理
│   │   ├── segmentation.py    # 打印/手写分离
│   │   └── enhancement.py     # 图像增强
│   ├── feature_extraction/    # 特征提取
│   │   ├── deep_features.py   # 深度学习特征
│   │   ├── traditional_features.py # 传统特征
│   │   └── feature_fusion.py  # 特征融合
│   ├── matching/              # 匹配算法
│   │   ├── similarity.py      # 相似度计算
│   │   └── matcher.py         # 匹配器
│   ├── training/              # 训练模块
│   │   └── trainer.py         # 模型训练器
│   ├── model/                 # 模型定义
│   │   └── siamese_network.py # Siamese网络
│   ├── grpc_server/           # gRPC服务
│   │   ├── server.py          # 服务入口
│   │   └── *.proto            # Protobuf定义
│   └── requirements.txt
│
├── frontend/                   # React前端
│   ├── src/
│   │   ├── components/        # 通用组件
│   │   │   ├── Layout.tsx     # 布局组件
│   │   │   └── ImageCropper.tsx # 图片裁剪
│   │   ├── pages/             # 页面组件
│   │   │   ├── Login.tsx      # 登录页
│   │   │   ├── Dashboard.tsx  # 仪表盘
│   │   │   ├── SampleList.tsx # 样本管理
│   │   │   ├── SampleUpload.tsx # 样本上传
│   │   │   ├── Recognition.tsx # 识别页面
│   │   │   └── ...
│   │   ├── services/          # API服务
│   │   ├── contexts/          # React上下文
│   │   └── types/             # TypeScript类型
│   └── package.json
│
├── desktop/                    # PyQt6桌面端
│   ├── ui/
│   │   └── main_window.py     # 主窗口（含拖拽、历史）
│   ├── api_client/
│   │   └── grpc_client.py     # gRPC客户端
│   └── requirements.txt
│
├── shared/                     # 共享模块
│   ├── proto/                 # Protobuf定义
│   ├── types.py               # 共享类型
│   └── constants.py           # 共享常量
│
├── docker/                     # Docker配置
│   ├── nginx/                 # Nginx配置
│   └── mysql/                 # MySQL初始化
│
├── docker-compose.yml          # Docker编排
└── .env.example               # 环境变量示例
```

---

## 本地开发

### 步骤1: 克隆项目

```bash
git clone <repository-url>
cd handwriting_recognition_system
```

### 步骤2: 环境配置

```bash
# 复制环境变量配置文件
cp .env.example .env

# 编辑配置（根据本地环境修改）
vim .env
```

主要配置项说明：

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=handwriting_recognition

# JWT配置（生产环境必须修改！）
SECRET_KEY=your-super-secret-key-at-least-32-characters

# 服务端口
BACKEND_PORT=8000
INFERENCE_PORT=50051
FRONTEND_PORT=3000
```

### 步骤3: 数据库设置

```bash
# 登录MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE handwriting_recognition 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

# 创建用户（可选）
CREATE USER 'handwriting'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON handwriting_recognition.* TO 'handwriting'@'localhost';
FLUSH PRIVILEGES;

# 退出MySQL
EXIT;
```

### 步骤4: 启动后端服务

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动服务（开发模式）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**常见问题解决：**

如果遇到 `libstdc++` 或 Python 环境问题：

```bash
# 方法1: 使用修复脚本
./fix_venv.sh

# 方法2: 使用启动脚本
./run_server.sh

# 方法3: 手动指定系统Python
/usr/bin/python3 -m uvicorn app.main:app --reload
```

### 步骤5: 启动推理服务

```bash
cd inference_service

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖（包括PyTorch）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 启动gRPC服务
python -m grpc_server.server
```

**GPU支持：**

```bash
# 如果有NVIDIA GPU，安装CUDA版本的PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 步骤6: 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:5173 启动。

### 步骤7: 启动桌面端（可选）

```bash
cd desktop

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动桌面应用
python main.py
```

### 注意事项

您可能需要更改以下内容：
```
backend/app/core/config.py 中 CORS_ORIGINS 以确保跨域访问正常
frontend/vite.config.ts 中 target 为您的后端地址（如果您需要在广域网访问，请填写公网地址）
```

### 开发模式下的服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端API | http://localhost:8000 | FastAPI服务 |
| API文档 | http://localhost:8000/docs | Swagger UI |
| 推理服务 | localhost:50051 | gRPC服务 |
| 前端 | http://localhost:5173 | Vite开发服务器 |

---

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

## Docker部署

### 快速启动（开发环境）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 生产环境部署

```bash
# 使用生产配置（包含Nginx）
docker-compose --profile production up -d

# 或者单独构建
docker-compose build
docker-compose up -d
```

### 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| mysql | 3306 | MySQL数据库 |
| redis | 6379 | Redis缓存 |
| backend | 8000 | 后端API |
| inference | 50051 | 推理服务(gRPC) |
| frontend | 3000 | 前端服务 |
| nginx | 80/443 | 反向代理(生产) |

### 数据持久化

Docker Compose 定义了以下数据卷：

```yaml
volumes:
  mysql_data:      # MySQL数据
  redis_data:      # Redis数据
  uploads_data:    # 上传文件
  models_data:     # 模型文件
```

### 环境变量覆盖

创建 `.env` 文件覆盖默认配置：

```bash
# 生产环境配置示例
SECRET_KEY=your-production-secret-key-very-long-and-random
MYSQL_ROOT_PASSWORD=strong_password_here
MYSQL_PASSWORD=another_strong_password
```

---

## API文档

### 认证接口

#### 用户注册
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "teacher1",
  "password": "password123",
  "role": "teacher",
  "school_id": 1
}
```

#### 用户登录
```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=teacher1&password=password123
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### 用户登出
```http
POST /api/auth/logout
Authorization: Bearer <token>
```

#### 获取当前用户
```http
GET /api/auth/me
Authorization: Bearer <token>
```

### 样本管理接口

#### 上传样本
```http
POST /api/samples/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@sample_image.jpg
```

#### 获取样本列表
```http
GET /api/samples?user_id=1&status=processed&limit=20
Authorization: Bearer <token>
```

#### 裁剪样本区域
```http
POST /api/samples/{sample_id}/crop
Authorization: Bearer <token>
Content-Type: application/json

{
  "bbox": {
    "x": 100,
    "y": 50,
    "width": 300,
    "height": 200
  }
}
```

### 识别接口

#### 识别字迹
```http
POST /api/recognition
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@test_image.jpg
top_k=5
```

响应：
```json
{
  "top_k": [
    {"user_id": 1, "username": "student1", "score": 0.95},
    {"user_id": 2, "username": "student2", "score": 0.72}
  ],
  "is_unknown": false,
  "confidence": 0.95
}
```

### 训练接口

#### 触发训练
```http
POST /api/training/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "force_retrain": false
}
```

#### 获取训练状态
```http
GET /api/training/status/{job_id}
Authorization: Bearer <token>
```

---

## 开发规范

### Git提交规范

使用语义化提交信息：

```bash
feat: 添加图片裁剪功能
fix: 修复登录token过期问题
docs: 更新API文档
style: 格式化代码
refactor: 重构特征提取模块
test: 添加单元测试
chore: 更新依赖版本
```

### Python代码规范

- 遵循 PEP 8 规范
- 使用类型注解
- 函数/类添加文档字符串

```python
def extract_features(image: np.ndarray, model: nn.Module) -> np.ndarray:
    """
    从图像中提取特征向量。
    
    Args:
        image: 输入图像，shape为(H, W, C)
        model: 特征提取模型
        
    Returns:
        特征向量，shape为(512,)
    """
    pass
```

### TypeScript代码规范

- 使用严格模式
- 定义接口类型
- 使用函数式组件

```typescript
interface SampleProps {
  id: number;
  imagePath: string;
  status: 'pending' | 'processed';
  onDelete: (id: number) => void;
}

const SampleCard: React.FC<SampleProps> = ({ id, imagePath, status, onDelete }) => {
  // ...
};
```

### 数据库迁移

创建新迁移：

```bash
cd backend
alembic revision --autogenerate -m "add_new_table"
alembic upgrade head
```

回滚迁移：

```bash
alembic downgrade -1
```

---

## 测试指南

### 后端测试

```bash
cd backend

# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/ -v

# 运行覆盖率测试
pytest --cov=app tests/
```

### 前端测试

```bash
cd frontend

# 运行测试
npm test

# 运行E2E测试
npm run test:e2e
```

### API测试

使用 Swagger UI 进行手动测试：
- 访问 http://localhost:8000/docs
- 点击 "Authorize" 输入token
- 测试各个接口

---

## 常见问题

### Q1: 后端启动报错 `libstdc++.so.6`

**原因**: Nix环境下的Python与系统库不兼容

**解决方案**:
```bash
cd backend
./fix_venv.sh  # 使用系统Python重建虚拟环境
```

### Q2: 数据库连接失败

**检查项**:
1. MySQL服务是否启动：`systemctl status mysql`
2. 数据库是否创建：`mysql -e "SHOW DATABASES;"`
3. 用户权限是否正确
4. `.env` 配置是否正确

### Q3: 推理服务连接超时

**检查项**:
1. 推理服务是否启动
2. 端口是否正确（默认50051）
3. 防火墙是否放行

```bash
# 测试gRPC连接
python -c "import grpc; ch = grpc.insecure_channel('localhost:50051'); print('OK')"
```

### Q4: 前端无法调用API

**检查项**:
1. 后端CORS配置是否包含前端地址
2. API地址是否正确
3. Token是否有效

```typescript
// 检查API配置
console.log(import.meta.env.VITE_API_URL);
```

### Q5: Docker构建失败

**常见原因**:
1. 网络问题导致依赖下载失败
2. 磁盘空间不足

**解决方案**:
```bash
# 清理Docker缓存
docker system prune -a

# 使用镜像加速
export DOCKER_BUILDKIT=1
```

### Q6: GPU不被识别

**检查项**:
1. NVIDIA驱动是否安装：`nvidia-smi`
2. CUDA版本是否匹配
3. PyTorch CUDA版本是否正确

```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.device_count())
```

---

## 联系方式

如有问题，请提交Issue或联系开发团队。

---

*最后更新: 2026-01-24*
