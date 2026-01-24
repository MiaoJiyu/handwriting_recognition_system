import grpc
from typing import Dict
import os
from core.config import settings

# 这里需要导入生成的gRPC代码
# from proto import handwriting_inference_pb2, handwriting_inference_pb2_grpc


class InferenceClient:
    """推理服务gRPC客户端"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.getenv("INFERENCE_HOST", "localhost")
        self.port = port or int(os.getenv("INFERENCE_PORT", "50051"))
        self.channel = None
    
    def _get_channel(self):
        """获取gRPC通道"""
        if self.channel is None:
            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
        return self.channel
    
    def recognize(self, image_path: str) -> Dict:
        """识别单张图片"""
        try:
            channel = self._get_channel()
            # stub = handwriting_inference_pb2_grpc.HandwritingInferenceStub(channel)
            
            # 读取图片数据
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 构建请求
            # request = handwriting_inference_pb2.RecognizeRequest(
            #     image_data=image_data,
            #     top_k=5
            # )
            
            # 调用服务
            # response = stub.Recognize(request)
            
            # 转换为字典
            # result = {
            #     "top_k": [
            #         {
            #             "user_id": r.user_id,
            #             "username": r.username,
            #             "score": r.score
            #         }
            #         for r in response.top_k
            #     ],
            #     "is_unknown": response.is_unknown,
            #     "confidence": response.confidence
            # }
            
            # 临时返回模拟结果
            result = {
                "top_k": [
                    {"user_id": 1, "username": "test_user", "score": 0.95}
                ],
                "is_unknown": False,
                "confidence": 0.95
            }
            
            return result
        except Exception as e:
            raise Exception(f"识别失败: {str(e)}")
