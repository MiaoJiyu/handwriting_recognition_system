from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.responses import Response
from contextlib import asynccontextmanager
from .core.config import settings
from .utils.logger import get_logger
from .utils.config_validator import validate_all_settings, print_validation_results
from .middleware.error_handler import error_handler_middleware
from .middleware.performance import PerformanceMiddleware
import os
from datetime import datetime
from .api import (
    auth_router,
    users_router,
    training_router,
    recognition_router,
    schools_router,
    samples_router,
    config_router,
    system_router,
    token_router,
    tokens_management_router,
    scheduled_tasks_router,
    quotas_router,
    monitoring_router
)
from .services.task_scheduler import task_scheduler

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("========== 应用启动 ==========")
    print("Starting application...")

    # 验证配置
    try:
        validation_results = validate_all_settings(settings)
        print_validation_results(validation_results)

        # 检查是否有失败的验证
        failed_validations = [k for k, v in validation_results.items() if not v]
        if failed_validations:
            error_msg = f"配置验证失败: {', '.join(failed_validations)}。请修正配置后重新启动应用。"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise

    # 启动任务调度器
    print("Starting task scheduler...")
    try:
        await task_scheduler.start()
        print("Task scheduler started successfully")
        logger.info("任务调度器启动成功")
    except Exception as e:
        print(f"Failed to start task scheduler: {e}")
        logger.error(f"任务调度器启动失败: {str(e)}")

    logger.info("应用启动完成")
    logger.info("========== 应用启动完成 ==========")

    yield

    # 关闭时
    print("Stopping application...")
    logger.info("========== 应用关闭 ==========")

    # 停止任务调度器
    print("Stopping task scheduler...")
    try:
        await task_scheduler.stop()
        print("Task scheduler stopped successfully")
        logger.info("任务调度器停止成功")
    except Exception as e:
        print(f"Failed to stop task scheduler: {e}")
        logger.error(f"任务调度器停止失败: {str(e)}")

    logger.info("应用关闭完成")
    logger.info("========== 应用关闭完成 ==========")


app = FastAPI(
    title="字迹识别系统API",
    description="基于Few-shot Learning的字迹识别系统后端API",
    version="2.0.0",
    lifespan=lifespan
)

# 添加性能监控中间件
app.add_middleware(PerformanceMiddleware)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加全局错误处理中间件（必须在CORS之后，作为第一个HTTP中间件）
@app.middleware("http")
async def error_handler_wrapper(request, call_next):
    from .middleware.error_handler import error_handler_middleware
    return await error_handler_middleware(request, call_next)

# 兜底：StaticFiles 响应有时不会被 CORSMiddleware 补齐 CORS 头（尤其是图片/跨域 canvas 场景）。
# 这里针对 /uploads/* 强制附加 CORS 响应头。
@app.middleware("http")
async def uploads_cors_middleware(request, call_next):
    if request.method == "OPTIONS" and request.url.path.startswith("/uploads/"):
        origin = request.headers.get("origin")
        headers = {}
        if origin and origin in settings.cors_origins_list:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Allow-Methods"] = "GET,OPTIONS"
            headers["Access-Control-Allow-Headers"] = request.headers.get("access-control-request-headers", "*")
        return Response(status_code=204, headers=headers)

    response = await call_next(request)
    if request.url.path.startswith("/uploads/"):
        origin = request.headers.get("origin")
        if origin and origin in settings.cors_origins_list:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# 静态文件：用于访问上传的样本图片
# 说明：StaticFiles 不会自动加 CORS 头；我们通过自定义 StaticFiles 给静态响应补充 CORS。
class CORSStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        # 对于静态文件，某些情况下 Origin 头不会出现在 scope['headers']（或大小写/代理导致缺失）。
        # 这里采用更稳妥策略：
        # - 如果有 Origin 且在白名单内：回显该 Origin
        # - 如果没有 Origin：不加 CORS（同源不需要）
        # - 如果 Origin 不在白名单：不加 CORS
        response = await super().get_response(path, scope)

        headers = dict(scope.get("headers") or [])
        origin_b = headers.get(b"origin")
        if not origin_b:
            return response

        origin = origin_b.decode("latin1")
        if origin in settings.cors_origins_list:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

# 让浏览器可以通过 /uploads/... 访问到 settings.UPLOAD_DIR 下的文件
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.SAMPLES_DIR, exist_ok=True)
app.mount("/uploads", CORSStaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 注册路由（统一添加 /api 前缀）
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(recognition_router, prefix="/api")
app.include_router(schools_router, prefix="/api")
app.include_router(samples_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(token_router, prefix="/api")
app.include_router(tokens_management_router, prefix="/api")
app.include_router(scheduled_tasks_router, prefix="/api")
app.include_router(quotas_router, prefix="/api")
app.include_router(monitoring_router)  # 监控路由已包含 /api 前缀


@app.get("/")
async def root():
    return {"message": "字迹识别系统API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
