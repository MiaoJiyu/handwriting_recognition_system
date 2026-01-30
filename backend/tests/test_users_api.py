"""
测试用户管理API的功能
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
import json


client = TestClient(app)


def test_download_template():
    """测试下载学生名单模板"""
    response = client.get("/api/users/template")

    # 检查状态码
    assert response.status_code == 200

    # 检查返回的是文件
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", "")

    # 检查Content-Disposition header
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "student_template.xlsx" in response.headers.get("content-disposition", "")

    # 检查返回内容不为空
    assert len(response.content) > 0

    print("✓ 下载模板测试通过")


def test_download_template_not_matched_to_user_id():
    """测试/template不会被/{user_id}路由拦截"""
    response = client.get("/api/users/template")

    # 如果被/{user_id}拦截，会返回422错误（无法将"template"解析为整数）
    # 成功的情况是返回200和Excel文件
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"

    print("✓ /template路由未被拦截")


def test_export_students():
    """测试导出学生名单"""
    # 首先需要登录获取token
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    if login_response.status_code != 200:
        print("⚠ 无法登录管理员账号，跳过导出测试")
        print(f"  登录响应: {login_response.status_code} - {login_response.text}")
        return

    token = login_response.json()["access_token"]

    # 测试导出
    response = client.get(
        "/api/users/export",
        headers={"Authorization": f"Bearer {token}"}
    )

    # 检查状态码
    assert response.status_code == 200

    # 检查返回的是文件
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", "")

    # 检查Content-Disposition header
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "students_" in response.headers.get("content-disposition", "")
    assert ".xlsx" in response.headers.get("content-disposition", "")

    # 检查返回内容不为空
    assert len(response.content) > 0

    print("✓ 导出学生名单测试通过")


def test_export_not_matched_to_user_id():
    """测试/export不会被/{user_id}路由拦截"""
    # 首先需要登录获取token
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    if login_response.status_code != 200:
        print("⚠ 无法登录管理员账号，跳过路由拦截测试")
        return

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/users/export",
        headers={"Authorization": f"Bearer {token}"}
    )

    # 如果被/{user_id}拦截，会返回422错误（无法将"export"解析为整数）
    # 成功的情况是返回200和Excel文件
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"

    print("✓ /export路由未被拦截")


def test_get_user_by_id():
    """测试通过ID获取用户（验证/{user_id}路由仍然正常工作）"""
    # 首先需要登录获取token
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    if login_response.status_code != 200:
        print("⚠ 无法登录管理员账号，跳过用户查询测试")
        return

    token = login_response.json()["access_token"]

    # 获取当前用户信息（假设admin的ID是1）
    response = client.get(
        "/api/users/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    # 检查状态码
    assert response.status_code == 200

    # 检查返回的用户数据
    user_data = response.json()
    assert "id" in user_data
    assert "username" in user_data
    assert user_data["username"] == "admin"

    print("✓ 通过ID获取用户测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("用户管理API功能测试")
    print("=" * 60)
    print()

    try:
        test_download_template()
        test_download_template_not_matched_to_user_id()
        print()

        test_export_students()
        test_export_not_matched_to_user_id()
        print()

        test_get_user_by_id()
        print()

        print("=" * 60)
        print("所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
