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

# 复用仓库根目录 inference_service 侧已存在的 pb2/pb2_grpc。
# 注意：当从 backend 目录运行（例如 uvicorn --reload）时，项目根目录不一定在 sys.path 中，
# 因此这里显式把仓库根目录和 grpc_server 目录加入 sys.path，确保可 import inference_service。
import sys

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_grpc_server_dir = os.path.join(_repo_root, "inference_service", "grpc_server")
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
if _grpc_server_dir not in sys.path:
    sys.path.insert(0, _grpc_server_dir)

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
    
    async def train_model(self, job_id: int, force_retrain: bool = False, school_id: Optional[int] = None, incremental: bool = False) -> dict:
        """触发训练（对接 gRPC TrainModel）"""
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.TrainRequest(job_id=job_id, force_retrain=force_retrain, school_id=school_id or 0, incremental=incremental)
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

    async def get_training_recommendation(self) -> dict:
        """获取训练建议（对接 gRPC GetTrainingRecommendation）"""
        channel = await self._get_channel()
        if self.stub is None:
            self.stub = pb2_grpc.HandwritingInferenceStub(channel)
        req = pb2.TrainingRecommendationRequest()
        resp = await self.stub.GetTrainingRecommendation(req)
        return {
            "should_train": getattr(resp, "should_train", False),
            "strategy": getattr(resp, "strategy", ""),
            "reason": getattr(resp, "reason", ""),
            "change_type": getattr(resp, "change_type", ""),
            "change_ratio": getattr(resp, "change_ratio", 0.0),
            "priority": getattr(resp, "priority", 0),
            "error_message": getattr(resp, "error_message", ""),
        }
