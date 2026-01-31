#!/bin/bash
# 强制关闭后端服务 (FastAPI/uvicorn)

echo "正在停止后端服务..."

# 查找并杀死 uvicorn 进程
PIDS=$(pgrep -f "uvicorn.*app.main:app" 2>/dev/null)

if [ -z "$PIDS" ]; then
    # 尝试查找其他可能的 FastAPI 进程
    PIDS=$(pgrep -f "python.*main.py" 2>/dev/null)
fi

if [ -z "$PIDS" ]; then
    echo "未找到运行中的后端服务"
    exit 0
fi

echo "发现后端进程: $PIDS"
pkill -9 -f "uvicorn.*app.main:app"

# 等待进程完全退出
sleep 2

# 检查是否还有残留进程
REMAINING=$(pgrep -f "uvicorn.*app.main:app" 2>/dev/null)
if [ -z "$REMAINING" ]; then
    # 尝试查找其他可能的 FastAPI 进程
    REMAINING=$(pgrep -f "python.*main.py" 2>/dev/null)
fi

if [ -z "$REMAINING" ]; then
    echo "✓ 后端服务已成功停止"
else
    echo "✗ 后端服务仍有残留进程: $REMAINING"
    exit 1
fi
