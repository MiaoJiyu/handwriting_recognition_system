#!/usr/bin/env python3
"""
生成Protobuf Python代码的脚本
"""
import os
import sys
import subprocess

# 设置库路径
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')

# 获取脚本目录
script_dir = os.path.dirname(os.path.abspath(__file__))
proto_file = os.path.join(script_dir, '../../shared/proto/handwriting_inference.proto')
proto_dir = os.path.join(script_dir, '../../shared/proto')

# 检查proto文件是否存在
if not os.path.exists(proto_file):
    print(f"错误: proto文件不存在: {proto_file}")
    print("请先创建 proto 文件")
    sys.exit(1)

# 切换到脚本目录
os.chdir(script_dir)

# 生成Python代码
print("生成Protobuf Python代码...")
print(f"Proto文件: {proto_file}")
print(f"输出目录: {script_dir}")

try:
    result = subprocess.run([
        sys.executable, '-m', 'grpc_tools.protoc',
        '--python_out=.',
        '--grpc_python_out=.',
        f'-I{proto_dir}',
        proto_file
    ], check=True, capture_output=True, text=True)
    
    print("成功生成Python代码！")
    print("生成的文件:")
    for f in ['handwriting_inference_pb2.py', 'handwriting_inference_pb2_grpc.py']:
        if os.path.exists(f):
            print(f"  - {f}")
        else:
            print(f"  - {f} (未找到)")
            
except subprocess.CalledProcessError as e:
    print(f"生成失败: {e}")
    print(f"错误输出: {e.stderr}")
    sys.exit(1)
except Exception as e:
    print(f"发生错误: {e}")
    sys.exit(1)
