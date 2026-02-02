from typing import Optional, Callable, Dict
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

from ..core.database import get_db
from ..services.quota_service import QuotaService
from ..models.user import UserRole

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件 - 拦截识别请求并检查配额"""

    def __init__(self, app, quota_service: QuotaService):
        super().__init__(app)
        self.quota_service = quota_service
        self.security = HTTPBearer(auto_error=False)

    async def dispatch(self, request: Request, call_next):
        # 只处理识别请求
        if request.url.path == "/api/recognition" and request.method == "POST":
            return await self._handle_recognition_request(request, call_next)

        # 其他请求直接通过
        return await call_next(request)

    async def _handle_recognition_request(self, request: Request, call_next):
        """处理识别请求的速率限制"""
        try:
            # 获取当前用户信息
            user_info = await self._get_user_from_request(request)
            if not user_info:
                # 如果没有用户信息，直接通过（依赖项会处理认证）
                return await call_next(request)

            user_id = user_info.get("user_id")
            user_role = user_info.get("role")
            school_id = user_info.get("school_id")

            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)

            try:
                # 检查配额
                is_allowed, deny_reason, usage_snapshot = self.quota_service.check_quota(
                    db=db,
                    user_id=user_id,
                    user_role=user_role,
                    school_id=school_id
                )

                if not is_allowed:
                    # 配额不足，拒绝请求
                    logger.warning(
                        f"Rate limit exceeded for user {user_id}: {deny_reason}",
                        extra={"usage_snapshot": usage_snapshot}
                    )

                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "识别次数超限",
                            "deny_reason": deny_reason,
                            "usage": usage_snapshot
                        }
                    )

                # 配额允许，记录配额信息到请求状态
                request.state.quota_checked = True
                request.state.user_id = user_id
                request.state.school_id = school_id
                request.state.user_quota = self.quota_service.get_or_create_user_quota(db, user_id, school_id)

                # 调用下一个中间件/路由处理器
                response = await call_next(request)

                return response

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # 出错时允许请求通过，避免影响正常使用
            return await call_next(request)

    async def _get_user_from_request(self, request: Request) -> Optional[Dict]:
        """从请求中获取用户信息"""
        # 这里需要根据实际的认证机制来获取用户信息
        # 由于FastAPI的依赖注入在中间件之后执行，我们需要手动解析JWT
        try:
            # 尝试从Authorization header获取token
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization[7:]

                # 这里应该验证JWT token并提取用户信息
                # 为了简化，这里假设已经有一个JWT验证函数
                # 在实际实现中，需要与auth.py中的verify_token逻辑保持一致

                # 暂时返回None，让依赖项处理认证
                # 后续可以通过请求状态传递用户信息
                pass

        except Exception as e:
            logger.debug(f"Failed to extract user from request: {e}")

        return None


class QuotaChecker:
    """配额检查器 - 在依赖项中使用"""

    def __init__(self, quota_service: QuotaService):
        self.quota_service = quota_service

    def __call__(self, db: Session, current_user: Dict) -> None:
        """
        检查用户配额
        如果配额不足，抛出HTTPException
        """
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        school_id = current_user.get("school_id")

        # 检查配额
        is_allowed, deny_reason, usage_snapshot = self.quota_service.check_quota(
            db=db,
            user_id=user_id,
            user_role=user_role,
            school_id=school_id
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "识别次数超限",
                    "deny_reason": deny_reason,
                    "usage": usage_snapshot
                }
            )


def check_rate_limit(
    quota_service: QuotaService = None
) -> Callable:
    """
    速率限制依赖项
    可以在路由中使用: Depends(check_rate_limit())
    """
    async def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: Dict = Depends(get_current_user)  # 需要导入get_current_user
    ):
        if not quota_service:
            quota_service = QuotaService()

        checker = QuotaChecker(quota_service)
        checker(db, current_user)

        return current_user

    return dependency
