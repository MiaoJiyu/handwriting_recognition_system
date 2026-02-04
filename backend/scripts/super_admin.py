"""
超级管理员命令行工具
提供绕过前端限制的超级管理员操作功能
使用方法：
    python scripts/super_admin.py <command> [args]

可用命令：
    delete <user_id>             - 强制删除用户（包括系统管理员）
    change_password <user_id> <new_password>  - 强制修改用户密码（包括系统管理员）
    update_role <user_id> <new_role>  - 强制修改用户角色
    delete_self                      - 强制删除当前登录用户（仅用于测试）
    change_self_password <new_password> - 修改当前用户密码（仅用于测试）
    list_users                      - 列出所有用户
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.utils.security import get_password_hash
from app.models.user import User, UserRole


def get_db_session():
    """创建数据库会话"""
    from sqlalchemy import create_engine
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def delete_user(user_id: int, force: bool = False):
    """
    强制删除用户（包括系统管理员）

    Args:
        user_id: 用户ID
        force: 是否强制删除（绕过所有检查）
    """
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ 用户不存在：ID={user_id}")
            return False

        print(f"删除用户：")
        print(f"  ID: {user.id}")
        print(f"  用户名: {user.username}")
        print(f"  昵称: {user.nickname}")
        print(f"  角色: {user.role.value}")
        print(f"  学校ID: {user.school_id}")

        if not force:
            # 确认操作
            confirm = input("\n⚠️  警告：这会永久删除该用户及其所有相关数据！\n确认删除？(yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ 已取消操作")
                return False

        # 删除用户
        session.delete(user)
        session.commit()

        print("✅ 用户删除成功")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ 删除失败：{str(e)}")
        return False
    finally:
        session.close()


def change_password(user_id: int, new_password: str, force: bool = False):
    """
    强制修改用户密码（包括系统管理员）

    Args:
        user_id: 用户ID
        new_password: 新密码
        force: 是否强制修改（绕过确认）
    """
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ 用户不存在：ID={user_id}")
            return False

        print(f"修改用户密码：")
        print(f"  ID: {user.id}")
        print(f"  用户名: {user.username}")
        print(f"  角色: {user.role.value}")

        if not force:
            # 确认操作
            confirm = input("\n⚠️  警告：这会修改该用户的登录密码！\n确认修改？(yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ 已取消操作")
                return False

        # 修改密码
        user.password_hash = get_password_hash(new_password)
        session.commit()

        print("✅ 密码修改成功")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ 修改失败：{str(e)}")
        return False
    finally:
        session.close()


def update_role(user_id: int, new_role: str, force: bool = False):
    """
    强制修改用户角色

    Args:
        user_id: 用户ID
        new_role: 新角色 (student/teacher/school_admin/system_admin)
        force: 是否强制修改（绕过确认）
    """
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ 用户不存在：ID={user_id}")
            return False

        print(f"修改用户角色：")
        print(f"  ID: {user.id}")
        print(f"  用户名: {user.username}")
        print(f"  当前角色: {user.role.value}")
        print(f"  新角色: {new_role}")

        # 验证新角色
        role_map = {
            'student': UserRole.STUDENT,
            'teacher': UserRole.TEACHER,
            'school_admin': UserRole.SCHOOL_ADMIN,
            'system_admin': UserRole.SYSTEM_ADMIN,
        }
        if new_role not in role_map:
            print(f"❌ 无效的角色：{new_role}")
            print("可用角色：student, teacher, school_admin, system_admin")
            return False

        new_role_enum = role_map[new_role]

        if not force:
            # 确认操作
            confirm = input("\n⚠️  警告：这会修改该用户的权限级别！\n确认修改？(yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ 已取消操作")
                return False

        # 修改角色
        user.role = new_role_enum
        session.commit()

        print("✅ 角色修改成功")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ 修改失败：{str(e)}")
        return False
    finally:
        session.close()


def list_users():
    """列出所有用户"""
    session = get_db_session()
    try:
        users = session.query(User).order_by(User.id).all()

        print(f"\n{'='*60}")
        print(f"用户列表（共 {len(users)} 个用户）")
        print(f"{'='*60}\n")

        for user in users:
            print(f"ID: {user.id:4d} | 用户名: {user.username:20s} | "
                  f"昵称: {user.nickname or '-':15s} | "
                  f"角色: {user.role.value:15s} | "
                  f"学校: {user.school_id or '-':5s}")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ 查询失败：{str(e)}")
    finally:
        session.close()


def delete_self(force: bool = False):
    """
    强制删除当前登录用户（仅用于测试）

    Args:
        force: 是否强制删除（绕过确认）
    """
    username = input("请输入要删除的用户的用户名: ")
    session = get_db_session()
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ 用户不存在：{username}")
            return False

        if not force:
            # 确认操作
            confirm = input(f"\n⚠️  警告：这将删除用户 '{username}' 及其所有数据！\n\n"
                       f"这是危险操作，仅用于测试目的。\n\n"
                       f"确认删除？(输入 'DELETE' 确认): ")
            if confirm != 'DELETE':
                print("❌ 已取消操作")
                return False

        session.delete(user)
        session.commit()

        print(f"✅ 用户 '{username}' 删除成功")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ 删除失败：{str(e)}")
        return False
    finally:
        session.close()


def change_self_password(force: bool = False):
    """
    修改当前用户密码（仅用于测试）

    Args:
        force: 是否强制修改（绕过确认）
    """
    username = input("请输入要修改密码的用户的用户名: ")
    new_password = input("请输入新密码: ")

    if len(new_password) < 6:
        print("❌ 密码长度至少6位")
        return False

    return change_password_by_username(username, new_password, force)


def change_password_by_username(username: str, new_password: str, force: bool = False):
    """
    通过用户名修改密码

    Args:
        username: 用户名
        new_password: 新密码
        force: 是否强制修改
    """
    session = get_db_session()
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ 用户不存在：{username}")
            return False

        print(f"修改用户密码：")
        print(f"  用户名: {user.username}")
        print(f"  当前角色: {user.role.value}")

        if not force:
            confirm = input("\n确认修改密码？(yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ 已取消操作")
                return False

        user.password_hash = get_password_hash(new_password)
        session.commit()

        print("✅ 密码修改成功")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ 修改失败：{str(e)}")
        return False
    finally:
        session.close()


def show_help():
    """显示帮助信息"""
    print(__doc__)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == 'delete':
        if len(sys.argv) < 3:
            print("❌ 用法: python super_admin.py delete <user_id> [--force]")
            sys.exit(1)
        user_id = int(sys.argv[2])
        force = '--force' in sys.argv
        delete_user(user_id, force)

    elif command == 'change_password':
        if len(sys.argv) < 4:
            print("❌ 用法: python super_admin.py change_password <user_id> <new_password> [--force]")
            sys.exit(1)
        user_id = int(sys.argv[2])
        new_password = sys.argv[3]
        force = '--force' in sys.argv
        change_password(user_id, new_password, force)

    elif command == 'update_role':
        if len(sys.argv) < 4:
            print("❌ 用法: python super_admin.py update_role <user_id> <new_role> [--force]")
            print("   new_role: student | teacher | school_admin | system_admin")
            sys.exit(1)
        user_id = int(sys.argv[2])
        new_role = sys.argv[3]
        force = '--force' in sys.argv
        update_role(user_id, new_role, force)

    elif command == 'delete_self':
        force = '--force' in sys.argv
        delete_self(force)

    elif command == 'change_self_password':
        force = '--force' in sys.argv
        change_self_password(force)

    elif command == 'list_users':
        list_users()

    elif command == 'help':
        show_help()

    else:
        print(f"❌ 未知命令：{command}")
        show_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
