import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_HOST: str = "0.0.0.0"
    GRPC_PORT: int = 50051
    MODEL_DIR: str = "./models"
    DEFAULT_MODEL_VERSION: str = "latest"
    SIMILARITY_THRESHOLD: float = 0.7
    GAP_THRESHOLD: float = 0.1
    TOP_K: int = 5
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/handwriting_recognition?charset=utf8mb4"
    BACKEND_ORIGIN: str = "http://127.0.0.1:8000"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    SAMPLES_DIR: str = "./uploads/samples"

    model_config = {
        "env_file": os.path.join(os.path.dirname(__file__), "..", ".env"),
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
