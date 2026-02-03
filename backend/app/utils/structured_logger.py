"""
结构化日志配置
支持JSON格式输出、日志轮转、多级别日志
"""
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger


class JsonFormatter(jsonlogger.JsonFormatter):
    """JSON格式化器，用于结构化日志"""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """添加自定义字段到日志记录"""
        super().add_fields(log_record, record, message_dict)

        # 添加时间戳
        log_record['timestamp'] = datetime.utcnow().isoformat()

        # 添加日志级别
        log_record['level'] = record.levelname

        # 添加模块信息
        log_record['module'] = record.name
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # 添加进程和线程信息
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread

        # 如果有异常信息，添加异常详情
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }


class StructuredLogger:
    """结构化日志管理器"""

    def __init__(
        self,
        name: str,
        log_dir: str = "./logs",
        log_level: str = "INFO",
        enable_json: bool = True,
        enable_console: bool = True,
        enable_file: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 10
    ):
        """
        初始化结构化日志管理器

        Args:
            name: 日志器名称
            log_dir: 日志目录
            log_level: 日志级别
            enable_json: 是否启用JSON格式
            enable_console: 是否输出到控制台
            enable_file: 是否输出到文件
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的备份文件数量
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper())
        self.enable_json = enable_json
        self.enable_console = enable_console
        self.enable_file = enable_file

        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)

        # 避免重复配置
        if self.logger.handlers:
            return

        # 创建格式化器
        if enable_json:
            self.json_formatter = JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        self.text_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 添加处理器
        if enable_console:
            self._add_console_handler()

        if enable_file:
            self._add_file_handlers(max_bytes, backup_count)

    def _add_console_handler(self):
        """添加控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)

        if self.enable_json:
            console_handler.setFormatter(self.json_formatter)
        else:
            console_handler.setFormatter(self.text_formatter)

        self.logger.addHandler(console_handler)

    def _add_file_handlers(self, max_bytes: int, backup_count: int):
        """添加文件处理器"""

        # 主日志文件（所有级别）
        main_handler = RotatingFileHandler(
            self.log_dir / f"{self.name}.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(self.log_level)
        main_handler.setFormatter(self.json_formatter if self.enable_json else self.text_formatter)
        self.logger.addHandler(main_handler)

        # 错误日志文件（ERROR及以上）
        error_handler = RotatingFileHandler(
            self.log_dir / f"{self.name}_error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.json_formatter if self.enable_json else self.text_formatter)
        self.logger.addHandler(error_handler)

        # 慢请求日志文件（用于性能监控）
        slow_handler = RotatingFileHandler(
            self.log_dir / f"{self.name}_slow.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        slow_handler.setLevel(logging.WARNING)
        slow_handler.setFormatter(self.json_formatter if self.enable_json else self.text_formatter)
        self.logger.addHandler(slow_handler)

    def _log_with_context(self, level: int, message: str, context: Dict[str, Any] = None):
        """带上下文的日志记录"""
        if context:
            extra = {**context}
            # 将context作为extra参数传递
            self.logger.log(level, message, extra=extra)
        else:
            self.logger.log(level, message)

    def debug(self, message: str, context: Dict[str, Any] = None):
        """DEBUG级别日志"""
        self._log_with_context(logging.DEBUG, message, context)

    def info(self, message: str, context: Dict[str, Any] = None):
        """INFO级别日志"""
        self._log_with_context(logging.INFO, message, context)

    def warning(self, message: str, context: Dict[str, Any] = None):
        """WARNING级别日志"""
        self._log_with_context(logging.WARNING, message, context)

    def error(self, message: str, context: Dict[str, Any] = None, exc_info: bool = False):
        """ERROR级别日志"""
        if exc_info:
            self.logger.error(message, exc_info=True, extra=context or {})
        else:
            self._log_with_context(logging.ERROR, message, context)

    def critical(self, message: str, context: Dict[str, Any] = None, exc_info: bool = False):
        """CRITICAL级别日志"""
        if exc_info:
            self.logger.critical(message, exc_info=True, extra=context or {})
        else:
            self._log_with_context(logging.CRITICAL, message, context)

    def performance(self, message: str, duration_ms: float, context: Dict[str, Any] = None):
        """性能日志"""
        perf_context = context or {}
        perf_context['duration_ms'] = duration_ms
        perf_context['log_type'] = 'performance'

        if duration_ms > 1000:
            self.warning(f"[PERFORMANCE] {message}", perf_context)
        else:
            self.info(f"[PERFORMANCE] {message}", perf_context)


def get_structured_logger(
    name: str,
    log_dir: str = "./logs",
    log_level: str = "INFO",
    **kwargs
) -> StructuredLogger:
    """
    获取结构化日志器实例

    Args:
        name: 日志器名称
        log_dir: 日志目录
        log_level: 日志级别
        **kwargs: 其他参数

    Returns:
        StructuredLogger实例
    """
    return StructuredLogger(name, log_dir, log_level, **kwargs)
