"""
测试切换用户功能的脚本
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_login():
    """测试登录获取token"""
    print_section("1. 测试登录")
    response = requests.post(f"{BASE_URL}/api/auth/login",
                       data=f"username={USERNAME}&password={PASSWORD}",
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✓ 登录成功")
        print(f"  Token: {token[:50]}...")
        return token
    else:
        print(f"✗ 登录失败: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

def test_get_me(token):
    """测试获取当前用户"""
    print_section("2. 测试 /auth/me 接口")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ /auth/me 响应:")
        print(f"  ID: {data.get('id')}")
        print(f"  Username: {data.get('username')}")
        print(f"  Role: {data.get('role')}")
        print(f"  is_switched: {data.get('is_switched')}")
        print(f"  original_user_id: {data.get('original_user_id')}")
        print(f"  created_at: {data.get('created_at')}")
        return data
    else:
        print(f"✗ /auth/me 失败: {response.status_code}")
        return None

def test_switch_user(token, target_user_id):
    """测试切换用户"""
    print_section(f"3. 测试切换用户到 ID={target_user_id}")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/users/switch_user?target_user_id={target_user_id}", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 切换成功:")
        print(f"  ID: {data.get('id')}")
        print(f"  Username: {data.get('username')}")
        print(f"  Role: {data.get('role')}")
        print(f"  is_switched: {data.get('is_switched')}")
        print(f"  original_user_id: {data.get('original_user_id')}")
        print(f"  created_at: {data.get('created_at')}")
    else:
        print(f"✗ 切换失败: {response.status_code}")
        print(f"  Response: {response.text}")
    return None

def main():
    print_section("切换用户功能测试")

    # 1. 登录获取token
    token = test_login()
    if not token:
        print_section("错误: 无法获取token")
        return

    # 2. 测试 /auth/me - 切换前
    print_section("切换前的用户信息:")
    user_before = test_get_me(token)

    # 3. 切换到学生(stu1, ID=4)
    print_section("正在切换到学生 stu1...")
    test_switch_user(token, 4)

    # 4. 切换后测试 /auth/me
    print_section("切换后的用户信息:")
    user_after = test_get_me(token)

    print_section("测试完成")
    print(f"当前用户ID: {user_after.get('id')}")
    print(f"当前用户角色: {user_after.get('role')}")

if __name__ == "__main__":
    main()
