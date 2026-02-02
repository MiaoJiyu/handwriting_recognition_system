from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.quota import Quota, QuotaUsageLog
from ..models.user import User, UserRole


class QuotaService:
    """配额管理服务 - 处理识别次数限制和速率限制"""

    @staticmethod
    def get_or_create_user_quota(db: Session, user_id: int, school_id: Optional[int] = None) -> Quota:
        """获取或创建用户配额"""
        quota = db.query(Quota).filter(
            and_(
                Quota.quota_type == "user",
                Quota.user_id == user_id
            )
        ).first()

        if not quota:
            quota = Quota(
                quota_type="user",
                user_id=user_id,
                school_id=school_id,
                minute_limit=0,  # 0表示无限制
                hour_limit=0,
                day_limit=0,
                month_limit=0,
                total_limit=0
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)

        return quota

    @staticmethod
    def get_or_create_school_quota(db: Session, school_id: int) -> Quota:
        """获取或创建学校配额"""
        quota = db.query(Quota).filter(
            and_(
                Quota.quota_type == "school",
                Quota.school_id == school_id
            )
        ).first()

        if not quota:
            quota = Quota(
                quota_type="school",
                school_id=school_id,
                minute_limit=0,
                hour_limit=0,
                day_limit=0,
                month_limit=0,
                total_limit=0
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)

        return quota

    @staticmethod
    def check_quota(
        db: Session,
        user_id: int,
        user_role: UserRole,
        school_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        检查配额是否允许识别请求
        返回: (is_allowed, deny_reason, usage_snapshot)
        """
        now = datetime.utcnow()

        # 获取用户配额
        user_quota = QuotaService.get_or_create_user_quota(db, user_id, school_id)

        # 如果有学校ID，也需要检查学校配额
        school_quota = None
        if school_id:
            school_quota = QuotaService.get_or_create_school_quota(db, school_id)

        # 更新配额使用统计（检查是否需要重置时间窗口）
        QuotaService._reset_time_windows(user_quota, now)
        if school_quota:
            QuotaService._reset_time_windows(school_quota, now)

        # 检查用户配额
        user_allowed, user_reason = QuotaService._check_single_quota(user_quota)

        if not user_allowed:
            return False, user_reason, QuotaService._get_usage_snapshot(user_quota)

        # 检查学校配额
        if school_quota:
            school_allowed, school_reason = QuotaService._check_single_quota(school_quota)

            if not school_allowed:
                return False, f"school_{school_reason}", QuotaService._get_usage_snapshot(school_quota)

        # 配额允许通过
        return True, None, {}

    @staticmethod
    def _reset_time_windows(quota: Quota, now: datetime):
        """重置时间窗口计数器"""
        # 重置分钟计数器
        if not quota.minute_reset_at or (now - quota.minute_reset_at).total_seconds() >= 60:
            quota.minute_used = 0
            quota.minute_reset_at = now

        # 重置小时计数器
        if not quota.hour_reset_at or (now - quota.hour_reset_at).total_seconds() >= 3600:
            quota.hour_used = 0
            quota.hour_reset_at = now

        # 重置天计数器
        if not quota.day_reset_at or quota.day_reset_at.date() != now.date():
            quota.day_used = 0
            quota.day_reset_at = now

        # 重置月计数器
        if not quota.month_reset_at or (
            quota.month_reset_at.year != now.year or
            quota.month_reset_at.month != now.month
        ):
            quota.month_used = 0
            quota.month_reset_at = now

    @staticmethod
    def _check_single_quota(quota: Quota) -> Tuple[bool, Optional[str]]:
        """检查单个配额是否允许请求"""
        # 检查分钟限制
        if quota.minute_limit > 0 and quota.minute_used >= quota.minute_limit:
            return False, "minute_limit"

        # 检查小时限制
        if quota.hour_limit > 0 and quota.hour_used >= quota.hour_limit:
            return False, "hour_limit"

        # 检查天限制
        if quota.day_limit > 0 and quota.day_used >= quota.day_limit:
            return False, "day_limit"

        # 检查月限制
        if quota.month_limit > 0 and quota.month_used >= quota.month_limit:
            return False, "month_limit"

        # 检查总次数限制
        if quota.total_limit > 0 and quota.total_used >= quota.total_limit:
            return False, "total_limit"

        return True, None

    @staticmethod
    def _get_usage_snapshot(quota: Quota) -> Dict:
        """获取配额使用快照"""
        return {
            "minute_used": quota.minute_used,
            "minute_limit": quota.minute_limit,
            "hour_used": quota.hour_used,
            "hour_limit": quota.hour_limit,
            "day_used": quota.day_used,
            "day_limit": quota.day_limit,
            "month_used": quota.month_used,
            "month_limit": quota.month_limit,
            "total_used": quota.total_used,
            "total_limit": quota.total_limit
        }

    @staticmethod
    def increment_quota_usage(
        db: Session,
        user_id: int,
        school_id: Optional[int],
        recognition_log_id: Optional[int],
        user_quota: Quota,
        school_quota: Optional[Quota],
        is_allowed: bool,
        deny_reason: Optional[str]
    ):
        """增加配额使用次数"""
        now = datetime.utcnow()

        # 增加用户配额使用
        QuotaService._increment_single_quota(user_quota, now)

        # 增加学校配额使用
        if school_quota:
            QuotaService._increment_single_quota(school_quota, now)

        # 记录配额使用日志
        log = QuotaUsageLog(
            user_id=user_id,
            school_id=school_id,
            quota_type="user",
            quota_id=user_quota.id,
            recognition_log_id=recognition_log_id,
            is_allowed=1 if is_allowed else 0,
            deny_reason=deny_reason,
            usage_snapshot=QuotaService._get_usage_snapshot(user_quota) if not is_allowed else None
        )

        db.add(log)
        db.commit()

    @staticmethod
    def _increment_single_quota(quota: Quota, now: datetime):
        """增加单个配额的使用次数"""
        quota.minute_used += 1
        quota.hour_used += 1
        quota.day_used += 1
        quota.month_used += 1
        quota.total_used += 1
        quota.updated_at = now

    @staticmethod
    def update_quota(
        db: Session,
        quota_id: int,
        minute_limit: Optional[int] = None,
        hour_limit: Optional[int] = None,
        day_limit: Optional[int] = None,
        month_limit: Optional[int] = None,
        total_limit: Optional[int] = None,
        description: Optional[str] = None
    ) -> Quota:
        """更新配额配置"""
        quota = db.query(Quota).filter(Quota.id == quota_id).first()
        if not quota:
            raise ValueError(f"Quota with id {quota_id} not found")

        if minute_limit is not None:
            quota.minute_limit = minute_limit
        if hour_limit is not None:
            quota.hour_limit = hour_limit
        if day_limit is not None:
            quota.day_limit = day_limit
        if month_limit is not None:
            quota.month_limit = month_limit
        if total_limit is not None:
            quota.total_limit = total_limit
        if description is not None:
            quota.description = description

        quota.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(quota)

        return quota

    @staticmethod
    def batch_update_user_quotas(
        db: Session,
        user_ids: list,
        minute_limit: int = 0,
        hour_limit: int = 0,
        day_limit: int = 0,
        month_limit: int = 0,
        total_limit: int = 0,
        description: Optional[str] = None
    ) -> int:
        """批量更新用户配额"""
        updated_count = 0
        for user_id in user_ids:
            quota = QuotaService.get_or_create_user_quota(db, user_id)
            quota.minute_limit = minute_limit
            quota.hour_limit = hour_limit
            quota.day_limit = day_limit
            quota.month_limit = month_limit
            quota.total_limit = total_limit
            if description:
                quota.description = description
            quota.updated_at = datetime.utcnow()
            updated_count += 1

        db.commit()
        return updated_count

    @staticmethod
    def batch_update_school_quotas(
        db: Session,
        school_ids: list,
        minute_limit: int = 0,
        hour_limit: int = 0,
        day_limit: int = 0,
        month_limit: int = 0,
        total_limit: int = 0,
        description: Optional[str] = None
    ) -> int:
        """批量更新学校配额"""
        updated_count = 0
        for school_id in school_ids:
            quota = QuotaService.get_or_create_school_quota(db, school_id)
            quota.minute_limit = minute_limit
            quota.hour_limit = hour_limit
            quota.day_limit = day_limit
            quota.month_limit = month_limit
            quota.total_limit = total_limit
            if description:
                quota.description = description
            quota.updated_at = datetime.utcnow()
            updated_count += 1

        db.commit()
        return updated_count

    @staticmethod
    def get_quota_usage_logs(
        db: Session,
        user_id: Optional[int] = None,
        school_id: Optional[int] = None,
        limit: int = 100
    ) -> list:
        """获取配额使用日志"""
        query = db.query(QuotaUsageLog)

        if user_id:
            query = query.filter(QuotaUsageLog.user_id == user_id)
        if school_id:
            query = query.filter(QuotaUsageLog.school_id == school_id)

        logs = query.order_by(QuotaUsageLog.created_at.desc()).limit(limit).all()

        return [
            {
                "id": log.id,
                "user_id": log.user_id,
                "school_id": log.school_id,
                "quota_type": log.quota_type,
                "quota_id": log.quota_id,
                "recognition_log_id": log.recognition_log_id,
                "is_allowed": log.is_allowed == 1,
                "deny_reason": log.deny_reason,
                "usage_snapshot": log.usage_snapshot,
                "created_at": log.created_at
            }
            for log in logs
        ]

    @staticmethod
    def reset_quota_usage(
        db: Session,
        quota_id: int,
        reset_type: str = "all"
    ):
        """重置配额使用次数
        reset_type: 'minute', 'hour', 'day', 'month', 'total', 'all'
        """
        quota = db.query(Quota).filter(Quota.id == quota_id).first()
        if not quota:
            raise ValueError(f"Quota with id {quota_id} not found")

        if reset_type in ["minute", "all"]:
            quota.minute_used = 0
        if reset_type in ["hour", "all"]:
            quota.hour_used = 0
        if reset_type in ["day", "all"]:
            quota.day_used = 0
        if reset_type in ["month", "all"]:
            quota.month_used = 0
        if reset_type in ["total", "all"]:
            quota.total_used = 0

        quota.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(quota)

        return quota
