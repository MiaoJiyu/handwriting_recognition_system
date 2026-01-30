"""
字迹识别调用次数限制中间件
"""
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from ..models.rate_limit import RateLimitConfig, RecognitionUsage
from ..models.user import User
from ..models.school import School


class RateLimitChecker:
    """调用次数限制检查器"""

    def __init__(self, db: Session):
        self.db = db

    def check_rate_limit(self, user: User) -> None:
        """检查用户是否超过调用限制"""
        # 获取用户的限制配置（优先级：用户特定 > 学校特定 > 全局默认）
        config = self._get_rate_limit_config(user)

        if not config:
            # 没有配置，使用默认值
            config = RateLimitConfig()

        # 检查各时间段的限制
        self._check_minute_limit(user, config.per_minute)
        self._check_hour_limit(user, config.per_hour)
        self._check_day_limit(user, config.per_day)
        self._check_total_limit(user, config.total_limit)

    def _get_rate_limit_config(self, user: User) -> Optional[RateLimitConfig]:
        """获取用户的限制配置"""
        # 1. 查找用户特定的配置
        config = self.db.query(RateLimitConfig).filter(
            RateLimitConfig.user_id == user.id
        ).first()

        if config:
            return config

        # 2. 查找学校特定的配置
        if user.school_id:
            config = self.db.query(RateLimitConfig).filter(
                RateLimitConfig.school_id == user.school_id,
                RateLimitConfig.user_id == None
            ).first()

            if config:
                return config

        # 3. 查找全局默认配置
        config = self.db.query(RateLimitConfig).filter(
            RateLimitConfig.user_id == None,
            RateLimitConfig.school_id == None
        ).first()

        return config

    def _check_minute_limit(self, user: User, limit: int):
        """检查每分钟限制"""
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)

        count = self.db.query(RecognitionUsage).filter(
            RecognitionUsage.user_id == user.id,
            RecognitionUsage.timestamp >= one_minute_ago,
            RecognitionUsage.success == 1
        ).count()

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"每分钟调用次数已达到限制（{limit}次），请稍后再试"
            )

    def _check_hour_limit(self, user: User, limit: int):
        """检查每小时限制"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        count = self.db.query(RecognitionUsage).filter(
            RecognitionUsage.user_id == user.id,
            RecognitionUsage.timestamp >= one_hour_ago,
            RecognitionUsage.success == 1
        ).count()

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"每小时调用次数已达到限制（{limit}次），请稍后再试"
            )

    def _check_day_limit(self, user: User, limit: int):
        """检查每天限制"""
        one_day_ago = datetime.utcnow() - timedelta(days=1)

        count = self.db.query(RecognitionUsage).filter(
            RecognitionUsage.user_id == user.id,
            RecognitionUsage.timestamp >= one_day_ago,
            RecognitionUsage.success == 1
        ).count()

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"每天调用次数已达到限制（{limit}次），请明天再试"
            )

    def _check_total_limit(self, user: User, limit: int):
        """检查总次数限制"""
        count = self.db.query(RecognitionUsage).filter(
            RecognitionUsage.user_id == user.id,
            RecognitionUsage.success == 1
        ).count()

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"总调用次数已达到限制（{limit}次），请联系管理员增加配额"
            )

    def record_usage(self, user: User, success: bool = True, error_message: Optional[str] = None):
        """记录使用情况"""
        usage = RecognitionUsage(
            user_id=user.id,
            school_id=user.school_id,
            timestamp=datetime.utcnow(),
            success=1 if success else 0,
            error_message=error_message
        )
        self.db.add(usage)
        self.db.commit()


def check_rate_limit_decorator(require_admin=False):
    """调用次数限制装饰器"""
    async def decorator(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        # 检查权限
        if require_admin and current_user.role.value not in ['system_admin', 'school_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )

        # 检查速率限制
        checker = RateLimitChecker(db)
        checker.check_rate_limit(current_user)

        return current_user

    return decorator
