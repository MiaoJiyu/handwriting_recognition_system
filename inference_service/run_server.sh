#!/bin/bash
# 启动推理服务gRPC服务器

# 设置库路径
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# 进入脚本所在目录（使用 pwd 替代 dirname 避免 Nix 环境问题）
cd /opt/handwriting_recognition_system/inference_service

# 激活虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 运行服务器
python grpc_server/server.py
