from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    UPLOAD_DIR: str = "./uploads"
    SAMPLES_DIR: str = "./uploads/samples"
    MODELS_DIR: str = "./models"
    
    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
