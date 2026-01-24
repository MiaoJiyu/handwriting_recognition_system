import os
import ctypes

# Fix for Nix Python library path issues
# Preload libstdc++ to ensure it's available for gRPC
libstdc_paths = [
    '/lib/x86_64-linux-gnu/libstdc++.so.6',
    '/usr/lib/x86_64-linux-gnu/libstdc++.so.6',
    '/usr/lib/gcc/x86_64-linux-gnu/13/libstdc++.so'
]
for lib_path in libstdc_paths:
    if os.path.exists(lib_path):
        try:
            ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
            break
        except OSError:
            continue

import grpc
import asyncio
from typing import List, Optional
from ..core.config import settings

# 这里将使用生成的gRPC客户端代码
# 暂时提供接口定义


class InferenceClient:
    """推理服务客户端"""
    
    def __init__(self):
        self.channel = None
        self.stub = None
    
    async def _get_channel(self):
        """获取gRPC通道"""
        if self.channel is None:
            self.channel = grpc.aio.insecure_channel(
                f"{settings.INFERENCE_SERVICE_HOST}:{settings.INFERENCE_SERVICE_PORT}"
            )
        return self.channel
    
    async def recognize(self, image_path: str) -> dict:
        """识别单张图片"""
        # TODO: 实现gRPC调用
        # channel = await self._get_channel()
        # stub = HandwritingInferenceStub(channel)
        # request = RecognizeRequest(image_path=image_path)
        # response = await stub.Recognize(request)
        # return response
        raise NotImplementedError("等待gRPC服务实现")
    
    async def batch_recognize(self, image_paths: List[str]) -> List[dict]:
        """批量识别"""
        # TODO: 实现gRPC调用
        raise NotImplementedError("等待gRPC服务实现")
    
    async def train_model(self, job_id: int, force_retrain: bool = False) -> dict:
        """触发训练"""
        # TODO: 实现gRPC调用
        raise NotImplementedError("等待gRPC服务实现")
    
    async def get_training_status(self, job_id: int) -> dict:
        """获取训练状态"""
        # TODO: 实现gRPC调用
        raise NotImplementedError("等待gRPC服务实现")
    
    async def update_config(self, config: dict) -> dict:
        """更新配置"""
        # TODO: 实现gRPC调用
        raise NotImplementedError("等待gRPC服务实现")
