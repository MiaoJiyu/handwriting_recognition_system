"""
测试用户API路由顺序是否正确
验证 /template 和 /export 路由不会被 /{user_id} 路由拦截
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import users


def test_route_order():
    """测试路由定义顺序"""
    routes = users.router.routes

    print("=" * 60)
    print("用户API路由列表")
    print("=" * 60)

    for route in routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            print(f"{methods:10s} {route.path}")

    print("=" * 60)

    # 检查 /template 和 /export 是否在 /{user_id} 之前
    template_index = None
    export_index = None
    user_id_index = None

    for i, route in enumerate(routes):
        if hasattr(route, 'path'):
            if '/template' in route.path and '/{' not in route.path:
                template_index = i
            elif '/export' in route.path and '/{' not in route.path:
                export_index = i
            elif '/{user_id}' in route.path:
                user_id_index = i

    print("\n路由顺序检查：")
    print("=" * 60)
    print(f"/template 路由索引: {template_index}")
    print(f"/export   路由索引: {export_index}")
    print(f"/{{user_id}} 路由索引: {user_id_index}")
    print("=" * 60)

    if template_index is not None and export_index is not None and user_id_index is not None:
        if template_index < user_id_index and export_index < user_id_index:
            print("✓ 路由顺序正确！/template 和 /export 在 /{user_id} 之前")
            return True
        else:
            print("✗ 路由顺序错误！/template 和 /export 必须在 /{user_id} 之前")
            return False
    else:
        print("✗ 未找到所有必需的路由")
        return False


if __name__ == "__main__":
    success = test_route_order()
    sys.exit(0 if success else 1)
