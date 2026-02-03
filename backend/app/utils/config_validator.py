"""
配置验证工具
用于在应用启动时验证所有关键配置项
"""
import os
from urllib.parse import urlparse
from typing import Dict, Any
from .logger import get_logger

logger = get_logger(__name__)


def validate_database_url(database_url: str) -> bool:
    """
    验证数据库URL格式和必要字段

    Args:
        database_url: 数据库连接URL

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果验证失败
    """
    try:
        parsed = urlparse(database_url)

        # 验证协议
        if parsed.scheme not in ['mysql+pymysql', 'postgresql', 'postgresql+psycopg2']:
            raise ValueError(
                f"不支持的数据库类型: {parsed.scheme}。"
                f"支持的类型: mysql+pymysql, postgresql"
            )

        # 验证主机名
        if not parsed.hostname:
            raise ValueError("数据库主机名不能为空")

        # 验证用户名和密码
        if not parsed.username or not parsed.password:
            raise ValueError("数据库用户名和密码不能为空")

        logger.info(f"数据库URL验证通过: {parsed.hostname}:{parsed.port or 3306}")
        return True

    except Exception as e:
        logger.error(f"数据库URL验证失败: {str(e)}")
        raise ValueError(f"无效的数据库URL: {str(e)}")


def validate_directory_exists(dir_path: str, dir_name: str = "目录") -> bool:
    """
    验证目录存在，不存在则尝试创建

    Args:
        dir_path: 目录路径
        dir_name: 目录名称（用于错误消息）

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果目录无法访问或创建
    """
    try:
        if not os.path.exists(dir_path):
            logger.info(f"创建目录: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        elif not os.path.isdir(dir_path):
            raise ValueError(f"{dir_name}路径不是目录: {dir_path}")

        # 检查目录是否可写
        test_file = os.path.join(dir_path, '.test_write')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            raise ValueError(f"{dir_name}目录不可写: {str(e)}")

        logger.info(f"{dir_name}目录验证通过: {dir_path}")
        return True

    except Exception as e:
        logger.error(f"{dir_name}目录验证失败: {str(e)}")
        raise ValueError(f"无法访问{dir_name}目录: {str(e)}")


def validate_jwt_secret(secret: str) -> bool:
    """
    验证JWT密钥强度

    Args:
        secret: JWT密钥

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果密钥不满足要求
    """
    if len(secret) < 32:
        raise ValueError(
            f"JWT密钥长度不足32字符，当前长度: {len(len)}。"
            f"建议使用至少32字符的随机密钥。"
        )

    insecure_defaults = [
        'your-super-secret-key',
        'secret',
        'password',
        'changeme',
        'admin',
        'root'
    ]

    if secret.lower() in insecure_defaults:
        raise ValueError(
            f"JWT密钥使用了不安全的默认值: {secret}。"
            f"请使用强密钥。"
        )

    logger.info("JWT密钥验证通过")
    return True


def validate_cors_origins(cors_origins: str) -> bool:
    """
    验证CORS配置

    Args:
        cors_origins: CORS源列表，逗号分隔

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果CORS配置无效
    """
    try:
        origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]

        if not origins:
            raise ValueError("CORS源列表不能为空")

        for origin in origins:
            if origin == '*':
                logger.warning("CORS配置为*（所有源），生产环境不推荐")
                continue

            parsed = urlparse(origin)
            if parsed.scheme not in ['http', 'https']:
                raise ValueError(
                    f"CORS源必须使用http或https协议: {origin}"
                )

        logger.info(f"CORS配置验证通过: {len(origins)}个源")
        return True

    except Exception as e:
        logger.error(f"CORS配置验证失败: {str(e)}")
        raise ValueError(f"无效的CORS配置: {str(e)}")


def validate_upload_size(max_size: int) -> bool:
    """
    验证上传大小配置

    Args:
        max_size: 最大上传大小（字节）

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果上传大小超出合理范围
    """
    min_size = 1024  # 1KB
    max_allowed = 100 * 1024 * 1024  # 100MB

    if max_size < min_size:
        raise ValueError(
            f"上传大小不能小于1KB: {max_size}字节"
        )

    if max_size > max_allowed:
        raise ValueError(
            f"上传大小不能超过100MB: {max_size}字节"
        )

    logger.info(f"上传大小配置验证通过: {max_size / (1024*1024):.1f}MB")
    return True


def validate_inference_service(host: str, port: int) -> bool:
    """
    验证推理服务配置

    Args:
        host: 推理服务主机
        port: 推理服务端口

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果配置无效
    """
    if not host:
        raise ValueError("推理服务主机不能为空")

    if not (1 <= port <= 65535):
        raise ValueError(
            f"推理服务端口必须在1-65535之间: {port}"
        )

    logger.info(f"推理服务配置验证通过: {host}:{port}")
    return True


def validate_redis_connection(redis_url: str) -> bool:
    """
    验证Redis连接配置

    Args:
        redis_url: Redis连接URL

    Returns:
        True 如果验证通过

    Raises:
        ValueError: 如果配置无效
    """
    try:
        parsed = urlparse(redis_url)

        if parsed.scheme not in ['redis', 'rediss']:
            raise ValueError(
                f"不支持的Redis协议: {parsed.scheme}"
            )

        if not parsed.hostname:
            raise ValueError("Redis主机不能为空")

        logger.info(f"Redis配置验证通过: {parsed.hostname}:{parsed.port or 6379}")
        return True

    except Exception as e:
        logger.error(f"Redis配置验证失败: {str(e)}")
        raise ValueError(f"无效的Redis配置: {str(e)}")


def validate_all_settings(settings: Any) -> Dict[str, bool]:
    """
    验证所有配置项

    Args:
        settings: 配置对象（来自config.py的settings实例）

    Returns:
        验证结果字典，key为配置项名称，value为验证结果（True/False）

    Example:
        ```python
        from app.utils.config_validator import validate_all_settings
        from app.core.config import settings

        results = validate_all_settings(settings)
        for name, passed in results.items():
            print(f"{name}: {'✓' if passed else '✗'}")
        ```
    """
    results = {}

    # 验证数据库配置
    try:
        validate_database_url(settings.DATABASE_URL)
        results['database'] = True
    except Exception:
        results['database'] = False

    # 验证JWT密钥
    try:
        validate_jwt_secret(settings.SECRET_KEY)
        results['jwt_secret'] = True
    except Exception:
        results['jwt_secret'] = False

    # 验证上传目录
    try:
        validate_directory_exists(settings.UPLOAD_DIR, '上传目录')
        results['upload_dir'] = True
    except Exception:
        results['upload_dir'] = False

    # 验证样本目录
    try:
        validate_directory_exists(settings.SAMPLES_DIR, '样本目录')
        results['samples_dir'] = True
    except Exception:
        results['samples_dir'] = False

    # 验证模型目录
    try:
        validate_directory_exists(settings.MODELS_DIR, '模型目录')
        results['models_dir'] = True
    except Exception:
        results['models_dir'] = False

    # 验证CORS配置
    try:
        validate_cors_origins(settings.CORS_ORIGINS)
        results['cors_origins'] = True
    except Exception:
        results['cors_origins'] = False

    # 验证上传大小
    try:
        validate_upload_size(settings.MAX_UPLOAD_SIZE)
        results['upload_size'] = True
    except Exception:
        results['upload_size'] = False

    # 验证推理服务配置
    try:
        validate_inference_service(
            settings.INFERENCE_SERVICE_HOST,
            settings.INFERENCE_SERVICE_PORT
        )
        results['inference_service'] = True
    except Exception:
        results['inference_service'] = False

    # 验证Redis（如果配置）
    if hasattr(settings, 'REDIS_HOST'):
        try:
            redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            validate_redis_connection(redis_url)
            results['redis'] = True
        except Exception:
            results['redis'] = False

    return results


def print_validation_results(results: Dict[str, bool]) -> None:
    """
    打印验证结果摘要

    Args:
        results: 验证结果字典
    """
    logger.info("========== 配置验证结果 ==========")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, is_valid in results.items():
        status = "✓ 通过" if is_valid else "✗ 失败"
        logger.info(f"  {name}: {status}")

    logger.info("=" * 30)
    logger.info(f"总计: {passed}/{total} 项验证通过")

    if passed < total:
        failed = [name for name, is_valid in results.items() if not is_valid]
        logger.error(f"配置验证失败的项: {', '.join(failed)}")
        logger.error("请修正配置后重新启动应用")
    else:
        logger.info("所有配置项验证通过 ✓")
