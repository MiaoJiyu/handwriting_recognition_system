"""
性能监控中间件
记录请求耗时、响应状态等性能指标
"""
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from collections import defaultdict
import threading
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self._metrics = defaultdict(list)
        self._lock = threading.Lock()

    def record_metric(self, metric_name: str, value: float, tags: dict = None):
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
metrics_collector = PerformanceMetrics()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录性能指标"""
        start_time = time.time()

        # 生成请求ID用于关联
        request_id = request.headers.get('X-Request-ID', f"{int(time.time() * 1000)}_{id(request)}")
        request.state.request_id = request_id

        try:
            # 执行请求
            response = await call_next(request)

            # 计算请求耗时
            duration = time.time() - start_time
            duration_ms = duration * 1000

            # 记录性能指标
            path = request.url.path
            method = request.method
            status_code = response.status_code

            # 记录请求耗时指标
            metric_name = f"http.{method.lower()}.{path.replace('/', '_')}"
            metrics_collector.record_metric(metric_name, duration_ms, {
                'method': method,
                'path': path,
                'status_code': status_code
            })

            # 记录通用指标
            metrics_collector.record_metric('http_request_duration_ms', duration_ms, {
                'method': method,
                'path': path,
                'status_code': status_code
            })

            # 记录请求计数
            metrics_collector.record_metric('http_requests_total', 1, {
                'method': method,
                'path': path,
                'status_code': str(status_code)
            })

            # 添加性能头到响应
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Process-Time'] = f"{duration:.4f}"

            # 记录详细日志
            logger.info(
                f"{method} {path} - {status_code} - {duration_ms:.2f}ms",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration_ms': duration_ms,
                    'client_host': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent')
                }
            )

            # 如果请求耗时超过阈值，记录警告
            if duration_ms > 1000:  # 1秒阈值
                logger.warning(
                    f"慢请求: {method} {path} - {duration_ms:.2f}ms",
                    extra={
                        'request_id': request_id,
                        'method': method,
                        'path': path,
                        'duration_ms': duration_ms
                    }
                )

            return response

        except Exception as e:
            # 计算异常请求的耗时
            duration = time.time() - start_time
            duration_ms = duration * 1000

            # 记录错误指标
            metrics_collector.record_metric('http_errors_total', 1, {
                'method': request.method,
                'path': request.url.path,
                'error': str(e)
            })

            logger.error(
                f"请求异常: {request.method} {request.url.path} - {str(e)} - {duration_ms:.2f}ms",
                exc_info=True,
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': duration_ms,
                    'error': str(e)
                }
            )
            raise
