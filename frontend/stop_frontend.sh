#!/bin/bash
# 强制关闭前端服务 (vite dev server)

echo "正在停止前端服务..."

# 查找并杀死 vite 进程
PIDS=$(pgrep -f "vite.*--host" 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "未找到运行中的前端服务"
    exit 0
fi

echo "发现前端进程: $PIDS"
pkill -9 -f "vite.*--host"

# 等待进程完全退出
sleep 2

# 检查是否还有残留进程
REMAINING=$(pgrep -f "vite.*--host" 2>/dev/null)
if [ -z "$REMAINING" ]; then
    echo "✓ 前端服务已成功停止"
else
    echo "✗ 前端服务仍有残留进程: $REMAINING"
    exit 1
fi
