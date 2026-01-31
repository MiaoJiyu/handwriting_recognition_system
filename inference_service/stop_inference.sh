#!/bin/bash
# 强制关闭推理服务 (gRPC server)

echo "正在停止推理服务..."

# 查找并杀死 gRPC server 进程
PIDS=$(pgrep -f "python.*grpc_server.*server" 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "未找到运行中的推理服务"
    exit 0
fi

echo "发现推理服务进程: $PIDS"
pkill -9 -f "python.*grpc_server.*server"

# 等待进程完全退出
sleep 2

# 检查是否还有残留进程
REMAINING=$(pgrep -f "python.*grpc_server.*server" 2>/dev/null)
if [ -z "$REMAINING" ]; then
    echo "✓ 推理服务已成功停止"
else
    echo "✗ 推理服务仍有残留进程: $REMAINING"
    exit 1
fi
