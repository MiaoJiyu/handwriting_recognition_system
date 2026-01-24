#!/bin/bash
echo "=== 数据库配置设置 ==="
echo ""
read -p "请输入MySQL root密码（留空使用默认'password'）: " mysql_password
mysql_password=${mysql_password:-password}

read -p "请输入数据库名称（默认: handwriting_recognition）: " db_name
db_name=${db_name:-handwriting_recognition}

cat > .env << ENVEOF
# 数据库配置
DATABASE_URL=mysql+pymysql://root:${mysql_password}@localhost:3306/${db_name}?charset=utf8mb4

# JWT配置
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 推理服务配置
INFERENCE_SERVICE_HOST=localhost
INFERENCE_SERVICE_PORT=50051

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 文件存储配置
UPLOAD_DIR=./uploads
SAMPLES_DIR=./uploads/samples
MODELS_DIR=./models

# CORS配置
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ENVEOF

echo ""
echo "✓ .env文件已创建！"
echo ""
echo "现在可以运行: alembic upgrade head"
