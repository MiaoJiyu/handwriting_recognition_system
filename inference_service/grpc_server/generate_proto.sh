#!/bin/bash
# 生成Protobuf Python代码

# 设置库路径
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

cd "$(dirname "$0")"

# 检查proto文件是否存在
PROTO_FILE="../../shared/proto/handwriting_inference.proto"
if [ ! -f "$PROTO_FILE" ]; then
    echo "错误: proto文件不存在: $PROTO_FILE"
    echo "请先创建 proto 文件"
    exit 1
fi

# 检查grpc_tools是否安装
if ! python -c "import grpc_tools" 2>/dev/null; then
    echo "错误: grpc_tools未安装。请运行: pip install grpcio-tools"
    exit 1
fi

# 生成Python代码
echo "生成Protobuf Python代码..."
python -m grpc_tools.protoc \
    --python_out=. \
    --grpc_python_out=. \
    -I../../shared/proto \
    "$PROTO_FILE"

if [ $? -eq 0 ]; then
    echo "成功生成Python代码！"
    echo "生成的文件:"
    ls -la handwriting_inference_pb2*.py 2>/dev/null || echo "未找到生成的文件"
else
    echo "生成失败！"
    exit 1
fi
