"""
缓存管理器
支持Redis和内存缓存，提供统一的缓存接口
"""
import json
from typing import Optional, Any
from ..logger import get_logger

logger = get_logger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，将使用内存缓存")


class CacheManager:
    """
    缓存管理器

    提供统一的缓存接口，自动在Redis和内存缓存之间切换
    如果Redis不可用，自动降级到内存缓存
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化缓存管理器

        Args:
            redis_url: Redis连接URL，如果为None则仅使用内存缓存
        """
        self.redis_client = None
        self.memory_cache = {}
        self.use_redis = False

        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    socket_keepalive=30
                )
                # 测试连接
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis缓存已启用")
            except Exception as e:
                logger.warning(f"Redis连接失败: {str(e)}，使用内存缓存")
                self.redis_client = None

        if not self.use_redis:
            logger.info("使用内存缓存")

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在则返回None

        Example:
            ```python
            cache = CacheManager()
            user_data = cache.get("user_123")
            if user_data:
                return user_data
            ```
        """
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"缓存数据JSON解析失败: {key}")
                        return value
                return None
            except Exception as e:
                logger.error(f"Redis读取失败: {str(e)}")
                return self.memory_cache.get(key)
        else:
            return self.memory_cache.get(key)

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300
    ) -> bool:
        """
        设置缓存数据

        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间（秒），默认5分钟

        Returns:
            True 如果设置成功

        Example:
            ```python
            cache = CacheManager()
            cache.set("user_123", {"name": "张三"}, ttl=600)
            ```
        """
        if self.use_redis and self.redis_client:
            try:
                serialized_value = json.dumps(value, ensure_ascii=False)
                self.redis_client.setex(key, ttl, serialized_value)
                return True
            except Exception as e:
                logger.error(f"Redis写入失败: {str(e)}")
                self.memory_cache[key] = value
                return True
        else:
            self.memory_cache[key] = value
            return True

    def delete(self, key: str) -> bool:
        """
        删除缓存数据

        Args:
            key: 缓存键

        Returns:
            True 如果删除成功

        Example:
            ```python
            cache = CacheManager()
            cache.delete("user_123")
            ```
        """
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis删除失败: {str(e)}")
        self.memory_cache.pop(key, None)
        return True

    def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在

        Args:
            key: 缓存键

        Returns:
            True 如果缓存键存在

        Example:
            ```python
            cache = CacheManager()
            if cache.exists("user_123"):
                data = cache.get("user_123")
            ```
        """
        if self.use_redis and self.redis_client:
            try:
                return self.redis_client.exists(key) == 1
            except Exception as e:
                logger.error(f"Redis exists查询失败: {str(e)}")
                return key in self.memory_cache
        else:
            return key in self.memory_cache

    def clear(self) -> bool:
        """
        清空所有缓存

        Returns:
            True 如果清空成功

        Example:
            ```python
            cache = CacheManager()
            cache.clear()
            ```
        """
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("Redis缓存已清空")
            except Exception as e:
                logger.error(f"Redis清空失败: {str(e)}")
        self.memory_cache.clear()
        logger.info("内存缓存已清空")
        return True

    def get_many(self, keys: list) -> dict:
        """
        批量获取缓存数据

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典，不存在的键不会出现在结果中

        Example:
            ```python
            cache = CacheManager()
            data = cache.get_many(["user_123", "user_456"])
            ```
        """
        result = {}
        if self.use_redis and self.redis_client:
            try:
                values = self.redis_client.mget(keys)
                for i, key in enumerate(keys):
                    if values[i] is not None:
                        try:
                            result[key] = json.loads(values[i])
                        except json.JSONDecodeError:
                            result[key] = values[i]
            except Exception as e:
                logger.error(f"Redis批量读取失败: {str(e)}")
                for key in keys:
                    if key in self.memory_cache:
                        result[key] = self.memory_cache[key]
        else:
            for key in keys:
                if key in self.memory_cache:
                    result[key] = self.memory_cache[key]
        return result

    def set_many(self, data: dict, ttl: int = 300) -> bool:
        """
        批量设置缓存数据

        Args:
            data: 键值对字典
            ttl: 过期时间（秒）

        Returns:
            True 如果设置成功

        Example:
            ```python
            cache = CacheManager()
            cache.set_many({
                "user_123": {"name": "张三"},
                "user_456": {"name": "李四"}
            }, ttl=600)
            ```
        """
        if self.use_redis and self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                for key, value in data.items():
                    serialized_value = json.dumps(value, ensure_ascii=False)
                    pipe.setex(key, ttl, serialized_value)
                pipe.execute()
                return True
            except Exception as e:
                logger.error(f"Redis批量写入失败: {str(e)}")
                self.memory_cache.update(data)
                return True
        else:
            self.memory_cache.update(data)
            return True


# 全局缓存实例（在需要时创建）
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """
    获取全局缓存管理器实例

    Returns:
        CacheManager实例
    """
    global _cache_manager
    if _cache_manager is None:
        from ..core.config import settings
        redis_url = None
        if hasattr(settings, 'REDIS_HOST'):
            redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        _cache_manager = CacheManager(redis_url)
    return _cache_manager


def reset_cache():
    """
    重置全局缓存管理器

    主要用于测试环境
    """
    global _cache_manager
    _cache_manager = None
