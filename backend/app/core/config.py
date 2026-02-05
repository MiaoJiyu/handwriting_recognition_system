from typing import List, Annotated
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        case_sensitive=True,
        extra="ignore",
    )


    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/handwriting_recognition?charset=utf8mb4"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 推理服务配置
    INFERENCE_SERVICE_HOST: str = "localhost"
    INFERENCE_SERVICE_PORT: int = 50051
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # 文件存储配置
    UPLOAD_DIR: str = "/opt/handwriting_recognition_system/uploads"
    SAMPLES_DIR: str = "/opt/handwriting_recognition_system/uploads/samples"
    MODELS_DIR: str = "/opt/handwriting_recognition_system/models"

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # CORS配置 - store as string to avoid JSON parsing issues
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS from string (JSON or comma-separated) to list."""
        if not self.CORS_ORIGINS or not self.CORS_ORIGINS.strip():
            return ["http://localhost:3000", "http://localhost:5173"]

        # Support wildcard to allow all origins
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]

        # Try to parse as JSON first
        try:
            parsed = json.loads(self.CORS_ORIGINS)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # If JSON parsing fails, treat as comma-separated string
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
    


settings = Settings()