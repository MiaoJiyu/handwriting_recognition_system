import os
from typing import Optional


class Settings:
    """配置类"""
    INFERENCE_HOST: str = os.getenv("INFERENCE_HOST", "localhost")
    INFERENCE_PORT: int = int(os.getenv("INFERENCE_PORT", "50051"))


settings = Settings()
