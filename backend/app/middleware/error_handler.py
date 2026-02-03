"""
全局异常处理中间件
捕获并统一处理所有未处理的异常
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """
    全局异常处理中间件

    捕获所有未处理的异常，返回统一的错误响应格式，
    并记录详细的日志信息

    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        响应对象（正常响应或错误响应）

    Example:
        在main.py中注册：
        ```python
        from app.middleware.error_handler import error_handler_middleware

        app.add_middleware(error_handler_middleware)
        ```
    """
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # 记录详细的错误信息
        logger.error(
            f"未处理的异常: {str(e)}",
            exc_info=True,
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else None
            }
        )

        # 返回统一的错误响应
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "内部服务器错误",
                "error": str(e),
                "path": request.url.path,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def validation_exception_handler(request: Request, exc):
    """
    验证异常处理器

    Args:
        request: 请求对象
        exc: 验证异常

    Returns:
        JSON响应
    """
    logger.warning(f"验证异常: {str(exc)}", extra={
        "path": request.url.path,
        "method": request.method
    })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "请求验证失败",
            "errors": str(exc),
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def http_exception_handler(request: Request, exc):
    """
    HTTP异常处理器

    Args:
        request: 请求对象
        exc: HTTPException

    Returns:
        JSON响应
    """
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}", extra={
        "path": request.url.path,
        "method": request.method
    })
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
