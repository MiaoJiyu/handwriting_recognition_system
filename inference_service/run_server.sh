#!/bin/bash
# 启动推理服务gRPC服务器

# 设置库路径
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# 进入脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境（如果存在）
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 运行服务器
python grpc_server/server.py
