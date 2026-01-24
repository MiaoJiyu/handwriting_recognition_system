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

# 复用 inference_service 侧已存在的（占位版）pb2/pb2_grpc，以便快速对接 localhost:50051。
# 注意：该 pb2 文件并非 protoc 生成的标准实现，但在当前仓库内服务端/客户端可保持一致。
from inference_service.grpc_server import handwriting_inference_pb2 as pb2
from inference_service.grpc_server import handwriting_inference_pb2_grpc as pb2_grpc

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
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.RecognizeRequest(image_path=image_path, top_k=5)
        resp = await self.stub.Recognize(req)
        return {
            "top_k": [
                {"user_id": r.user_id, "username": r.username, "score": r.score}
                for r in getattr(resp, "top_k", [])
            ],
            "is_unknown": getattr(resp, "is_unknown", False),
            "confidence": getattr(resp, "confidence", 0.0),
            "error_message": getattr(resp, "error_message", ""),
        }
    
    async def batch_recognize(self, image_paths: List[str]) -> List[dict]:
        """批量识别"""
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.BatchRecognizeRequest()
        req.image_paths = list(image_paths)
        req.top_k = 5
        resp = await self.stub.BatchRecognize(req)
        results = []
        for r in getattr(resp, "results", []):
            results.append(
                {
                    "top_k": [
                        {"user_id": x.user_id, "username": x.username, "score": x.score}
                        for x in getattr(r, "top_k", [])
                    ],
                    "is_unknown": getattr(r, "is_unknown", False),
                    "confidence": getattr(r, "confidence", 0.0),
                    "error_message": getattr(r, "error_message", ""),
                }
            )
        return results
    
    async def train_model(self, job_id: int, force_retrain: bool = False) -> dict:
        """触发训练（对接 gRPC TrainModel）"""
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.TrainRequest(job_id=job_id, force_retrain=force_retrain)
        resp = await self.stub.TrainModel(req)
        return {
            "success": getattr(resp, "success", False),
            "message": getattr(resp, "message", ""),
            "job_id": getattr(resp, "job_id", job_id),
        }
    
    async def get_training_status(self, job_id: int) -> dict:
        """获取训练状态（对接 gRPC GetTrainingStatus）"""
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.TrainingStatusRequest(job_id=job_id)
        resp = await self.stub.GetTrainingStatus(req)
        return {
            "status": getattr(resp, "status", ""),
            "progress": getattr(resp, "progress", 0.0),
            "model_version_id": getattr(resp, "model_version_id", None) or None,
            "error_message": getattr(resp, "error_message", "") or None,
        }
    
    async def update_config(self, config: dict) -> dict:
        """更新配置（对接 gRPC UpdateConfig）"""
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.ConfigUpdateRequest(**config)
        resp = await self.stub.UpdateConfig(req)
        return {
            "success": getattr(resp, "success", False),
            "message": getattr(resp, "message", ""),
        }
