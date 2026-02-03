"""
Common serializers for API responses
"""
from pydantic import BaseModel, field_serializer
from datetime import datetime
from typing import Optional


class DateTimeMixin:
    """
    日期时间字段序列化混入类

    为所有包含datetime字段的响应模型提供统一的序列化方法
    自动将datetime对象转换为ISO格式字符串
    """

    @field_serializer('created_at', 'updated_at', 'deleted_at', mode='wrap')
    def serialize_datetime(self, value: Optional[datetime], _info):
        """序列化datetime字段为ISO格式字符串"""
        return value.isoformat() if value else None
