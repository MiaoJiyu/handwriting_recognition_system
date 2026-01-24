# Protobuf 代码生成说明

## 问题
如果遇到 `libstdc++.so.6` 错误，需要设置环境变量后再生成代码。

## 生成方法

### 方法1：使用 Python 脚本（推荐）
```bash
cd /opt/handwriting_recognition_system/inference_service/grpc_server
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
python generate_proto.py
```

### 方法2：使用 bash 脚本
```bash
cd /opt/handwriting_recognition_system/inference_service/grpc_server
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
bash generate_proto.sh
```

### 方法3：直接使用 protoc 命令
```bash
cd /opt/handwriting_recognition_system/inference_service/grpc_server
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
python -m grpc_tools.protoc \
    --python_out=. \
    --grpc_python_out=. \
    -I../../shared/proto \
    ../../shared/proto/handwriting_inference.proto
```

## 注意
- 如果仍然无法生成，当前的占位文件（handwriting_inference_pb2.py 和 handwriting_inference_pb2_grpc.py）可以让服务器运行
- 但为了完整功能，建议生成真正的 protobuf 代码
