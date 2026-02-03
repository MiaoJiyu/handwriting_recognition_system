"""
推理服务性能监控
"""
import time
import logging
from functools import wraps
from typing import Callable, Any, Dict
from collections import defaultdict
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager


class InferenceMetrics:
    """推理服务性能指标收集器"""

    def __init__(self):
        self._metrics = defaultdict(list)
        self._lock = threading.Lock()

    def record_metric(self, metric_name: str, value: float, tags: Dict[str, Any] = None):
        """记录指标"""
        with self._lock:
            self._metrics[metric_name].append({
                'value': value,
                'timestamp': datetime.utcnow(),
                'tags': tags or {}
            })

    def get_metrics(self, metric_name: str, minutes: int = 5) -> list:
        """获取指定时间范围内的指标"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        with self._lock:
            return [
                m for m in self._metrics.get(metric_name, [])
                if m['timestamp'] >= cutoff_time
            ]

    def get_average(self, metric_name: str, minutes: int = 5) -> float:
        """计算平均值"""
        metrics = self.get_metrics(metric_name, minutes)
        if not metrics:
            return 0.0
        return sum(m['value'] for m in metrics) / len(metrics)

    def get_percentile(self, metric_name: str, percentile: float = 95, minutes: int = 5) -> float:
        """计算百分位数"""
        metrics = self.get_metrics(metric_name, minutes)
        if not metrics:
            return 0.0
        values = sorted(m['value'] for m in metrics)
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]

    def clear_old_metrics(self, hours: int = 24):
        """清理旧指标数据"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        with self._lock:
            for metric_name in list(self._metrics.keys()):
                self._metrics[metric_name] = [
                    m for m in self._metrics[metric_name]
                    if m['timestamp'] >= cutoff_time
                ]


# 全局指标收集器
inference_metrics = InferenceMetrics()


def monitor_inference(metric_name: str):
    """
    推理性能监控装饰器

    Args:
        metric_name: 指标名称

    Usage:
        @monitor_inference('recognize_duration')
        async def recognize(image_path):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                duration_ms = duration * 1000

                # 记录成功指标
                inference_metrics.record_metric(f"{metric_name}_duration_ms", duration_ms, {
                    'status': 'success'
                })
                inference_metrics.record_metric(f"{metric_name}_count", 1, {
                    'status': 'success'
                })

                return result
            except Exception as e:
                duration = time.time() - start_time
                duration_ms = duration * 1000

                # 记录失败指标
                inference_metrics.record_metric(f"{metric_name}_duration_ms", duration_ms, {
                    'status': 'error',
                    'error': str(e)
                })
                inference_metrics.record_metric(f"{metric_name}_errors", 1, {
                    'error': str(e)
                })

                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                duration_ms = duration * 1000

                # 记录成功指标
                inference_metrics.record_metric(f"{metric_name}_duration_ms", duration_ms, {
                    'status': 'success'
                })
                inference_metrics.record_metric(f"{metric_name}_count", 1, {
                    'status': 'success'
                })

                return result
            except Exception as e:
                duration = time.time() - start_time
                duration_ms = duration * 1000

                # 记录失败指标
                inference_metrics.record_metric(f"{metric_name}_duration_ms", duration_ms, {
                    'status': 'error',
                    'error': str(e)
                })
                inference_metrics.record_metric(f"{metric_name}_errors", 1, {
                    'error': str(e)
                })

                raise

        # 根据函数类型返回对应的包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def monitor_operation(operation_name: str, logger: logging.Logger):
    """
    操作性能监控上下文管理器

    Args:
        operation_name: 操作名称
        logger: 日志记录器

    Usage:
        with monitor_operation('feature_extraction', logger):
            features = extract_features(image)
    """
    start_time = time.time()
    logger.info(f"开始执行: {operation_name}")

    try:
        yield

        duration = time.time() - start_time
        duration_ms = duration * 1000

        # 记录成功指标
        inference_metrics.record_metric(f"{operation_name}_duration_ms", duration_ms, {
            'status': 'success'
        })

        logger.info(f"完成执行: {operation_name} - {duration_ms:.2f}ms")

        if duration_ms > 1000:
            logger.warning(f"慢操作: {operation_name} - {duration_ms:.2f}ms")

    except Exception as e:
        duration = time.time() - start_time
        duration_ms = duration * 1000

        # 记录失败指标
        inference_metrics.record_metric(f"{operation_name}_duration_ms", duration_ms, {
            'status': 'error',
            'error': str(e)
        })
        inference_metrics.record_metric(f"{operation_name}_errors", 1, {
            'error': str(e)
        })

        logger.error(f"执行失败: {operation_name} - {str(e)} - {duration_ms:.2f}ms")
        raise


def log_performance(logger: logging.Logger, metric_name: str, duration_ms: float,
                   extra_info: Dict[str, Any] = None):
    """
    记录性能日志

    Args:
        logger: 日志记录器
        metric_name: 指标名称
        duration_ms: 耗时（毫秒）
        extra_info: 额外信息
    """
    log_data = {
        'metric': metric_name,
        'duration_ms': duration_ms,
        **(extra_info or {})
    }

    if duration_ms > 1000:
        logger.warning(f"慢操作: {metric_name} - {duration_ms:.2f}ms", extra=log_data)
    else:
        logger.info(f"操作完成: {metric_name} - {duration_ms:.2f}ms", extra=log_data)

    # 记录到指标收集器
    inference_metrics.record_metric(f"{metric_name}_duration_ms", duration_ms)
