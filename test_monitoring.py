#!/usr/bin/env python
"""
测试性能监控系统
"""
import time
import requests
import random

BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    try:
        # 简单健康检查
        response = requests.get(f"{BASE_URL}/api/monitoring/health")
        print(f"简单健康检查: {response.status_code}")
        print(response.json())

        # 详细健康检查
        response = requests.get(f"{BASE_URL}/api/monitoring/health?detailed=true")
        print(f"\n详细健康检查: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"健康检查失败: {e}")

def test_performance_metrics():
    """测试性能指标"""
    print("\n=== 测试性能指标 ===")
    try:
        # 获取所有指标
        response = requests.get(f"{BASE_URL}/api/monitoring/metrics")
        print(f"获取所有指标: {response.status_code}")
        print(response.json())

        # 获取特定指标
        response = requests.get(f"{BASE_URL}/api/monitoring/metrics?metric_name=http_request_duration_ms&minutes=5")
        print(f"\n获取特定指标: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"获取性能指标失败: {e}")

def test_system_stats():
    """测试系统统计"""
    print("\n=== 测试系统统计 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/stats")
        print(f"获取系统统计: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"获取系统统计失败: {e}")

def test_log_query():
    """测试日志查询"""
    print("\n=== 测试日志查询 ===")
    try:
        # 查询所有日志
        response = requests.get(f"{BASE_URL}/api/monitoring/logs?limit=10")
        print(f"查询所有日志: {response.status_code}")
        data = response.json()
        print(f"日志数量: {len(data['data'])}")
        for log in data['data'][:3]:
            print(f"  {log[:100]}...")

        # 查询ERROR级别日志
        response = requests.get(f"{BASE_URL}/api/monitoring/logs?level=ERROR&limit=10")
        print(f"\n查询ERROR日志: {response.status_code}")
        data = response.json()
        print(f"ERROR日志数量: {len(data['data'])}")

        # 关键词搜索
        response = requests.get(f"{BASE_URL}/api/monitoring/logs?keyword=识别&limit=10")
        print(f"\n关键词搜索: {response.status_code}")
        data = response.json()
        print(f"匹配日志数量: {len(data['data'])}")
    except Exception as e:
        print(f"查询日志失败: {e}")

def test_clear_metrics():
    """测试清理指标"""
    print("\n=== 测试清理指标 ===")
    try:
        response = requests.post(f"{BASE_URL}/api/monitoring/clear-old-metrics?hours=24")
        print(f"清理指标: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"清理指标失败: {e}")

def generate_test_traffic():
    """生成测试流量"""
    print("\n=== 生成测试流量 ===")
    endpoints = [
        "/",
        "/health",
        "/api/monitoring/health",
        "/api/monitoring/stats"
    ]

    print("发送测试请求...")
    for i in range(20):
        endpoint = random.choice(endpoints)
        try:
            start_time = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}")
            duration = time.time() - start_time
            print(f"  [{i+1}] {endpoint} - {response.status_code} - {duration*1000:.2f}ms")
            time.sleep(random.uniform(0.1, 0.5))
        except Exception as e:
            print(f"  [{i+1}] {endpoint} - 失败: {e}")

def main():
    """主测试函数"""
    print("=" * 50)
    print("性能监控系统测试")
    print("=" * 50)

    # 检查后端是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("错误: 后端服务未正常响应")
            return
    except Exception as e:
        print(f"错误: 无法连接到后端服务: {e}")
        print("请确保后端服务正在运行: cd backend && ./run_server.sh")
        return

    # 生成测试流量
    generate_test_traffic()

    # 等待一下让指标收集
    time.sleep(2)

    # 运行测试
    test_health_check()
    test_performance_metrics()
    test_system_stats()
    test_log_query()

    # 可选: 测试清理指标
    # test_clear_metrics()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
