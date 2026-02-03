"""
统一API响应格式和异常类
提供一致的API响应格式和自定义异常
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from pydantic import BaseModel
from datetime import datetime


class APIResponse(BaseModel):
    """
    统一API响应格式

    Attributes:
        success: 操作是否成功
        message: 响应消息
        data: 响应数据（可选）
        errors: 错误详情（可选）
        timestamp: 响应时间戳
    """
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[Dict] = None
    timestamp: str


def success_response(
    message: str = "操作成功",
    data: Any = None
) -> dict:
    """
    生成成功响应

    Args:
        message: 成功消息
        data: 响应数据

    Returns:
        符合统一格式的响应字典

    Example:
        ```python
        from app.utils.response import success_response

        return success_response("创建用户成功", {"user_id": 123})
        ```
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def error_response(
    message: str,
    errors: Optional[Dict] = None,
    status_code: int = 400
) -> dict:
    """
    生成错误响应

    Args:
        message: 错误消息
        errors: 错误详情字典
        status_code: HTTP状态码

    Returns:
        符合统一格式的错误响应字典

    Example:
        ```python
        from app.utils.response import error_response

        return error_response(
            message="验证失败",
            errors={"username": "用户名已存在"},
            status_code=422
        )
        ```
    """
    return {
        "success": False,
        "message": message,
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat()
    }


class APIError(HTTPException):
    """
    自定义API异常基类

    Attributes:
        message: 错误消息
        status_code: HTTP状态码
        errors: 错误详情
    """
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        errors: Optional[Dict] = None
    ):
        super().__init__(
            status_code=status_code,
            detail=error_response(message, errors, status_code)
        )


class ValidationError(APIError):
    """
    验证错误 (422)

    用于请求数据验证失败的情况

    Attributes:
        message: 错误消息
        field: 出错字段（可选）
        errors: 错误详情（可选）
    """
    def __init__(
        self,
        message: str = "请求数据验证失败",
        field: Optional[str] = None,
        errors: Optional[Dict] = None
    ):
        error_dict = {}
        if field:
            error_dict["field"] = field
        if errors:
            error_dict.update(errors)
        super().__init__(message, status_code=422, errors=error_dict or None)


class NotFoundError(APIError):
    """
    资源未找到错误 (404)

    用于请求的资源不存在的情况

    Args:
        message: 错误消息，默认为"资源未找到"
    """
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message, status_code=404)


class UnauthorizedError(APIError):
    """
    未授权错误 (401)

    用于未提供有效认证的情况

    Args:
        message: 错误消息，默认为"未授权访问"
    """
    def __init__(self, message: str = "未授权访问"):
        super().__init__(message, status_code=401)


class ForbiddenError(APIError):
    """
    禁止访问错误 (403)

    用于有认证但权限不足的情况

    Args:
        message: 错误消息，默认为"无权访问"
    """
    def __init__(self, message: str = "无权访问"):
        super().__init__(message, status_code=403)


class ConflictError(APIError):
    """
    冲突错误 (409)

    用于资源冲突的情况（如重复创建）

    Args:
        message: 错误消息，默认为"资源冲突"
    """
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, status_code=409)


class InternalServerError(APIError):
    """
    内部服务器错误 (500)

    用于服务器内部错误

    Args:
        message: 错误消息，默认为"内部服务器错误"
    """
    def __init__(self, message: str = "内部服务器错误"):
        super().__init__(message, status_code=500)


class TooManyRequestsError(APIError):
    """
    请求过多错误 (429)

    用于请求频率超限的情况

    Args:
        message: 错误消息，默认为"请求频率超限"
    """
    def __init__(self, message: str = "请求频率超限"):
        super().__init__(message, status_code=429)


class FileUploadError(APIError):
    """
    文件上传错误 (413 或 400)

    用于文件上传失败的情况

    Args:
        message: 错误消息
        status_code: HTTP状态码，默认400
    """
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code=status_code)


class QuotaExceededError(APIError):
    """
    配额超限错误 (429)

    用于配额用尽的情况

    Args:
        message: 错误消息
        quota_info: 配额信息
    """
    def __init__(
        self,
        message: str = "配额已用尽",
        quota_info: Optional[Dict] = None
    ):
        errors = {"quota_info": quota_info} if quota_info else None
        super().__init__(message, status_code=429, errors=errors)


class ImageProcessingError(APIError):
    """
    图像处理错误 (500)

    用于图像处理失败的情况

    Args:
        message: 错误消息
    """
    def __init__(self, message: str = "图像处理失败"):
        super().__init__(message, status_code=500)


class TrainingError(APIError):
    """
    训练错误 (500)

    用于模型训练失败的情况

    Args:
        message: 错误消息
    """
    def __init__(self, message: str = "模型训练失败"):
        super().__init__(message, status_code=500)
