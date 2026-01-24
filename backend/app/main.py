from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from .core.config import settings
from .api import (
    auth_router,
    users_router,
    training_router,
    recognition_router,
    schools_router,
    samples_router
)

app = FastAPI(
    title="字迹识别系统API",
    description="基于Few-shot Learning的字迹识别系统后端API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.mount("/uploads", CORSStaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 注册路由
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(training_router)
app.include_router(recognition_router)
app.include_router(schools_router)
app.include_router(samples_router)


@app.get("/")
async def root():
    return {"message": "字迹识别系统API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
