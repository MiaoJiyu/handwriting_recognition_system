from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from .config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


def test_database_connection(engine) -> bool:
    """
    测试数据库连接是否正常

    Args:
        engine: SQLAlchemy engine实例

    Returns:
        True 如果连接测试成功

    Raises:
        RuntimeError: 如果连接测试失败
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as status"))
            status = result.scalar()
            if status == 1:
                logger.info("数据库连接测试成功")
                return True
            else:
                raise RuntimeError("数据库连接测试返回异常状态")
    except Exception as e:
        logger.error(f"数据库连接测试失败: {str(e)}", exc_info=True)
        raise RuntimeError(
            f"无法连接到数据库。请检查配置: {str(e)}"
        )


def get_pool_size() -> int:
    """
    根据环境确定合适的连接池大小

    Returns:
        连接池大小
    """
    # 默认连接池大小
    return 20


def get_max_overflow() -> int:
    """
    根据环境确定最大溢出连接数

    Returns:
        最大溢出连接数
    """
    # 默认最大溢出连接数
    return 10


# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # 连接健康检查
    pool_recycle=3600,         # 1小时后回收连接，防止连接长时间占用
    pool_size=get_pool_size(),   # 连接池大小
    max_overflow=get_max_overflow(),  # 最大溢出连接数
    echo=False,                 # 不输出SQL语句
    connect_args={
        'charset': 'utf8mb4',
        'connect_timeout': 10
    }
)

# 启动时验证数据库连接
try:
    test_database_connection(engine)
except RuntimeError as e:
    logger.critical(f"应用启动失败: {str(e)}")
    raise

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """
    数据库会话依赖

    提供统一的数据库会话管理，包括：
    - 自动提交
    - 错误时自动回滚
    - 确保会话关闭

    Yields:
        Session: SQLAlchemy session

    Example:
        ```python
        from app.core.database import get_db

        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
        ```
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        logger.error(f"数据库操作错误: {str(e)}", exc_info=True)
        raise
    finally:
        # 确保会话关闭
        db.close()
