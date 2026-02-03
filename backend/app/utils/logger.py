"""
统一日志记录工具
"""
import sys
import logging
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_file: Optional[str] = None, log_level: str = "INFO") -> logging.Logger:
    """
    配置并返回一个logger实例

    Args:
        name: logger名称，通常使用模块的__name__
        log_file: 日志文件路径（可选），如果提供将同时输出到文件
        log_level: 日志级别，默认为INFO

    Returns:
        配置好的logger实例

    Example:
        ```python
        from app.utils.logger import setup_logger

        logger = setup_logger(__name__)
        logger.info("应用启动")
        ```
    """
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(getattr(logging, log_level.upper()))

    # 创建格式化器
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器（使用简单格式）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_path = Path(log_file)
        # 确保日志目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已配置的logger实例（如果已配置则直接返回，否则使用默认配置）

    Args:
        name: logger名称

    Returns:
        logger实例
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # 如果没有配置过，使用默认配置
        return setup_logger(name)
    return logger
