# Systemd 服务管理配置

本目录包含用于管理字迹识别系统的 systemd 服务配置文件。

## 服务文件

- `/etc/systemd/system/handwriting-backend.service` - 后端 API 服务
- `/etc/systemd/system/handwriting-inference.service` - 推理服务 (gRPC)

## 管理脚本

`/opt/handwriting_recognition_system/manage_services.sh` - 服务管理脚本（交互式菜单）

## 快速开始

### 1. 首次配置

```bash
# 设置脚本可执行权限
chmod +x /opt/handwriting_recognition_system/manage_services.sh

# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable handwriting-backend.service
sudo systemctl enable handwriting-inference.service
```

### 2. 启动服务

**方式一：使用管理脚本（推荐）**
```bash
sudo ./manage_services.sh
```

**方式二：直接使用 systemctl 命令**
```bash
# 启动所有服务
sudo systemctl start handwriting-backend.service handwriting-inference.service

# 查看服务状态
sudo systemctl status handwriting-backend.service
sudo systemctl status handwriting-inference.service
```

### 3. 常用命令

```bash
# 启动服务
sudo systemctl start handwriting-backend.service
sudo systemctl start handwriting-inference.service

# 停止服务
sudo systemctl stop handwriting-backend.service
sudo systemctl stop handwriting-inference.service

# 重启服务
sudo systemctl restart handwriting-backend.service
sudo systemctl restart handwriting-inference.service

# 查看服务状态
sudo systemctl status handwriting-backend.service
sudo systemctl status handwriting-inference.service

# 查看实时日志
sudo journalctl -u handwriting-backend.service -f
sudo journalctl -u handwriting-inference.service -f

# 查看最近100条日志
sudo journalctl -u handwriting-backend.service -n 100
sudo journalctl -u handwriting-inference.service -n 100

# 启用/禁用开机自启
sudo systemctl enable handwriting-backend.service
sudo systemctl disable handwriting-backend.service
```

## 服务依赖关系

- **后端服务**: 依赖于网络和 MySQL 服务
- **推理服务**: 依赖于网络，建议在后端服务启动后启动

启动顺序：
1. MySQL 数据库
2. 后端 API 服务 (handwriting-backend)
3. 推理服务 (handwriting-inference)

## 环境配置

服务使用 `/opt/handwriting_recognition_system/.env` 文件中的环境变量配置。

重要配置项：
- `DATABASE_URL` - 数据库连接地址
- `INFERENCE_SERVICE_HOST` - 推理服务地址
- `INFERENCE_SERVICE_PORT` - 推理服务端口
- `UPLOAD_DIR` - 上传文件目录
- `MODELS_DIR` - 模型文件目录

修改 `.env` 文件后需要重启服务：
```bash
sudo systemctl restart handwriting-backend.service handwriting-inference.service
```

## 故障排查

### 1. 服务无法启动

检查服务日志：
```bash
sudo journalctl -u handwriting-backend.service -n 50 --no-pager
sudo journalctl -u handwriting-inference.service -n 50 --no-pager
```

常见问题：
- 虚拟环境未正确配置：检查 `venv` 目录是否存在
- 端口被占用：检查端口 8000 和 50051 是否被其他进程占用
- 依赖项缺失：确保 `requirements.txt` 中的所有依赖已安装

### 2. 服务频繁重启

检查服务配置：
```bash
# 查看服务详细状态
systemctl status handwriting-backend.service -l
systemctl status handwriting-inference.service -l
```

查看详细日志：
```bash
sudo journalctl -xeu handwriting-backend.service
sudo journalctl -xeu handwriting-inference.service
```

### 3. 权限问题

服务使用 `www-data` 用户运行。确保以下目录具有正确的权限：
```bash
sudo chown -R www-data:www-data /opt/handwriting_recognition_system/uploads
sudo chown -R www-data:www-data /opt/handwriting_recognition_system/models
```

## 安全配置

服务文件包含以下安全设置：
- `NoNewPrivileges=true` - 禁止获取新权限
- `PrivateTmp=true` - 使用私有 /tmp 目录
- `ProtectSystem=strict` - 保护系统目录
- `ProtectHome=true` - 保护用户主目录
- `ReadWritePaths` - 仅允许写入必要的目录

如需修改权限设置，请编辑相应的 `.service` 文件，然后运行：
```bash
sudo systemctl daemon-reload
sudo systemctl restart handwriting-backend.service
```

## 日志管理

Systemd 日志保存在 `/var/log/journal/`，可以使用 `journalctl` 命令查看。

查看特定时间段的日志：
```bash
# 查看今天的日志
sudo journalctl -u handwriting-backend.service --since today

# 查看最近1小时的日志
sudo journalctl -u handwriting-backend.service --since "1 hour ago"

# 查看特定时间范围的日志
sudo journalctl -u handwriting-backend.service --since "2026-02-04 08:00" --until "2026-02-04 12:00"
```

## 性能优化

### 调整重启策略

如需调整重启策略，编辑 `.service` 文件中的以下参数：
```ini
Restart=always           # 总是重启
RestartSec=10            # 重启间隔（秒）
Restart=on-failure       # 仅在失败时重启
```

### 内存限制

如需限制服务内存使用，在 `[Service]` 段落添加：
```ini
MemoryLimit=2G
MemoryMax=4G
```

## 更新服务配置

修改 `.service` 文件后，执行以下步骤：
```bash
# 1. 重载 systemd 配置
sudo systemctl daemon-reload

# 2. 重启服务
sudo systemctl restart handwriting-backend.service handwriting-inference.service
```

## 与 Nginx 的配合

前端静态文件由 Nginx 直接提供，后端 API 服务监听在 8000 端口。

Nginx 配置应包含以下内容：
- 前端静态文件：`/opt/handwriting_recognition_system/frontend/dist/`
- 后端 API 代理：`http://localhost:8000`

## 备份与恢复

### 备份服务配置
```bash
sudo cp /etc/systemd/system/handwriting-*.service /backup/
```

### 恢复服务配置
```bash
sudo cp /backup/handwriting-*.service /etc/systemd/system/
sudo systemctl daemon-reload
```
