-- 字迹识别系统数据库初始化脚本

-- 设置字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 确保数据库使用UTF8MB4
ALTER DATABASE handwriting_recognition CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- 授予权限
GRANT ALL PRIVILEGES ON handwriting_recognition.* TO 'handwriting'@'%';
FLUSH PRIVILEGES;

-- 注意：实际的表结构将由Alembic迁移脚本创建
-- 这个脚本只负责初始化数据库设置
