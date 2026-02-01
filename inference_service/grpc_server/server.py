import os
import sys
import ctypes

# Add inference_service directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

import asyncio
import grpc
from concurrent import futures
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import protobuf modules from local grpc_server package
from grpc_server import handwriting_inference_pb2, handwriting_inference_pb2_grpc
from core.config import settings
from inference.recognizer import Recognizer
from training.trainer import Trainer

logger.info(f"Inference service DATABASE_URL: {getattr(settings, 'DATABASE_URL', None)}")


class HandwritingInferenceServicer(handwriting_inference_pb2_grpc.HandwritingInferenceServicer):
    """gRPC服务实现"""
    
    def __init__(self):
        self.recognizer = Recognizer()
        self.trainer = Trainer()
    
    async def Recognize(self, request, context):
        """单张图片识别"""
        try:
            # 获取图片数据
            if request.image_path:
                image_path = request.image_path
            elif request.image_data:
                # 如果提供的是二进制数据，需要先保存
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    tmp.write(request.image_data)
                    image_path = tmp.name
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("必须提供image_path或image_data")
                return handwriting_inference_pb2.RecognizeResponse()
            
            # 执行识别
            top_k = request.top_k if request.top_k > 0 else settings.TOP_K
            result = await self.recognizer.recognize(image_path, top_k=top_k)
            
            # 构建响应
            response = handwriting_inference_pb2.RecognizeResponse()
            for r in result["top_k"]:
                recognition_result = handwriting_inference_pb2.RecognitionResult(
                    user_id=r["user_id"],
                    username=r.get("username", ""),
                    score=r["score"]
                )
                response.top_k.append(recognition_result)
            
            response.is_unknown = result["is_unknown"]
            response.confidence = result["confidence"]
            
            # 清理临时文件
            if not request.image_path and request.image_data:
                os.unlink(image_path)
            
            return response
        except Exception as e:
            logger.error(f"识别失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.RecognizeResponse(
                error_message=str(e)
            )
    
    async def BatchRecognize(self, request, context):
        """批量识别"""
        try:
            image_paths = []
            temp_files = []
            
            # 处理图片路径或数据
            if request.image_paths:
                image_paths = list(request.image_paths)
            elif request.image_data:
                import tempfile
                import os
                for img_data in request.image_data:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    tmp.write(img_data)
                    tmp.close()
                    image_paths.append(tmp.name)
                    temp_files.append(tmp.name)
            
            if not image_paths:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("必须提供image_paths或image_data")
                return handwriting_inference_pb2.BatchRecognizeResponse()
            
            # 批量识别
            top_k = request.top_k if request.top_k > 0 else settings.TOP_K
            results = await self.recognizer.batch_recognize(image_paths, top_k=top_k)
            
            # 构建响应
            response = handwriting_inference_pb2.BatchRecognizeResponse()
            for result in results:
                recognize_response = handwriting_inference_pb2.RecognizeResponse()
                for r in result["top_k"]:
                    recognition_result = handwriting_inference_pb2.RecognitionResult(
                        user_id=r["user_id"],
                        username=r.get("username", ""),
                        score=r["score"]
                    )
                    recognize_response.top_k.append(recognition_result)
                recognize_response.is_unknown = result["is_unknown"]
                recognize_response.confidence = result["confidence"]
                response.results.append(recognize_response)
            
            # 清理临时文件
            for tmp_file in temp_files:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            
            return response
        except Exception as e:
            logger.error(f"批量识别失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.BatchRecognizeResponse(
                error_message=str(e)
            )
    
    async def TrainModel(self, request, context):
        """触发训练"""
        try:
            job_id = request.job_id
            force_retrain = request.force_retrain

            # 异步启动训练任务，并确保异常被捕获，否则会出现 "Task exception was never retrieved"
            task = asyncio.create_task(self.trainer.train(job_id, force_retrain))

            def _log_task_result(t: asyncio.Task):
                try:
                    t.result()
                except Exception as e:
                    logger.error(f"训练任务异常 (job_id={job_id}): {str(e)}")

            task.add_done_callback(_log_task_result)

            return handwriting_inference_pb2.TrainResponse(
                success=True,
                message="训练任务已启动",
                job_id=job_id
            )
        except Exception as e:
            logger.error(f"启动训练失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.TrainResponse(
                success=False,
                message=str(e)
            )
    
    async def GetTrainingStatus(self, request, context):
        """获取训练状态"""
        try:
            job_id = request.job_id
            status = await self.trainer.get_status(job_id)
            
            return handwriting_inference_pb2.TrainingStatusResponse(
                status=status["status"],
                progress=status["progress"],
                error_message=status.get("error_message", ""),
                model_version_id=status.get("model_version_id", 0)
            )
        except Exception as e:
            logger.error(f"获取训练状态失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.TrainingStatusResponse(
                status="failed",
                error_message=str(e)
            )
    
    async def UpdateConfig(self, request, context):
        """更新配置"""
        try:
            if request.similarity_threshold > 0:
                settings.SIMILARITY_THRESHOLD = request.similarity_threshold
            if request.gap_threshold > 0:
                settings.GAP_THRESHOLD = request.gap_threshold
            if request.top_k > 0:
                settings.TOP_K = request.top_k

            return handwriting_inference_pb2.ConfigResponse(
                success=True,
                message="配置已更新"
            )
        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.ConfigResponse(
                success=False,
                message=str(e)
            )

    async def UpdateUserFeaturesIncremental(self, request, context):
        """增量更新用户特征"""
        try:
            user_id = request.user_id
            image_paths = list(request.image_paths)
            use_existing_pca = request.use_existing_pca

            # 查询这些样本的详细信息
            from sqlalchemy import create_engine, text
            engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

            with engine.connect() as conn:
                placeholders = ', '.join([':path' + str(i) for i in range(len(image_paths))])
                params = {f'path{i}': path for i, path in enumerate(image_paths)}

                result = conn.execute(text(f"""
                    SELECT s.id, s.user_id, s.image_path, s.extracted_region_path,
                           sr.bbox
                    FROM samples s
                    LEFT JOIN sample_regions sr ON s.id = sr.sample_id
                    WHERE s.image_path IN ({placeholders})
                      AND s.status = 'PROCESSED'
                      AND s.user_id = :user_id
                """), {**params, 'user_id': user_id})

                new_samples = []
                for row in result:
                    annotation_data = None
                    if row[4]:  # bbox
                        import json
                        annotation_data = {"bbox": json.loads(row[4])}

                    new_samples.append({
                        "id": row[0],
                        "user_id": row[1],
                        "image_path": row[2],
                        "extracted_region_path": row[3],
                        "annotation_data": annotation_data,
                        "separation_mode": "auto"
                    })

            # 调用增量特征更新
            success = await self.trainer.update_user_features_incremental(
                new_samples,
                user_id,
                use_existing_pca
            )

            if success:
                return handwriting_inference_pb2.IncrementalFeatureUpdateResponse(
                    success=True,
                    message=f"用户 {user_id} 的特征已增量更新",
                    user_id=user_id,
                    updated_sample_count=len(new_samples)
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("增量更新失败")
                return handwriting_inference_pb2.IncrementalFeatureUpdateResponse(
                    success=False,
                    message="增量更新失败",
                    user_id=user_id,
                    updated_sample_count=0
                )

        except Exception as e:
            logger.error(f"增量更新用户特征失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.IncrementalFeatureUpdateResponse(
                success=False,
                message=str(e),
                user_id=request.user_id,
                updated_sample_count=0
            )

    async def GetTrainingRecommendation(self, request, context):
        """获取训练建议"""
        try:
            recommendation = await self.trainer.get_training_recommendation()

            return handwriting_inference_pb2.TrainingRecommendationResponse(
                should_train=recommendation.get("should_train", False),
                strategy=recommendation.get("strategy", ""),
                reason=recommendation.get("reason", ""),
                change_type=recommendation.get("change_type", ""),
                change_ratio=recommendation.get("change_ratio", 0.0),
                priority=recommendation.get("priority", 0)
            )
        except Exception as e:
            logger.error(f"获取训练建议失败: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return handwriting_inference_pb2.TrainingRecommendationResponse(
                should_train=False,
                strategy="",
                reason="",
                change_type="",
                change_ratio=0.0,
                priority=0,
                error_message=str(e)
            )


async def serve():
    """启动gRPC服务器"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    handwriting_inference_pb2_grpc.add_HandwritingInferenceServicer_to_server(
        HandwritingInferenceServicer(), server
    )

    listen_addr = f"{settings.GRPC_HOST}:{settings.GRPC_PORT}"
    server.add_insecure_port(listen_addr)

    logger.info(f"gRPC服务器启动在 {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        try:
            await server.stop(grace=3)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
