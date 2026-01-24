# 字迹识别系统

一个基于Few-shot Learning的字迹识别系统，用于识别作业上的字迹归属。

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

## 用户角色

- 系统管理员：管理所有学校、用户
- 学校管理员：管理本校教师和学生
- 教师：上传样本、训练、识别作业
- 学生：查看自己的样本和识别记录
