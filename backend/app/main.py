from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
