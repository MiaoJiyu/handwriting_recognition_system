"""
测试样本裁剪功能
验证：
1. 裁剪后保存裁剪区域
2. 重新打开裁剪页面时显示已保存的裁剪区域
3. 裁剪后图片被正确保存
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
import json


client = TestClient(app)


def test_login():
    """登录获取token"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"⚠ 登录失败: {response.status_code} - {response.text}")
        return None


def test_upload_sample(token: str):
    """上传测试样本"""
    # 创建一个简单的测试图片
    import io
    from PIL import Image
    import numpy as np

    # 创建一个100x100的RGB图片
    img = Image.new('RGB', (100, 100), color='white')
    # 添加一些文本
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Test Sample", fill='black')

    # 保存到内存
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    # 上传
    files = {'file': ('test_sample.jpg', img_bytes, 'image/jpeg')}
    response = client.post(
        "/api/samples/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )

    if response.status_code == 201:
        return response.json()
    else:
        print(f"⚠ 上传失败: {response.status_code} - {response.text}")
        return None


def test_crop_sample(token: str, sample_id: int):
    """测试裁剪样本"""
    # 第一次裁剪
    crop_data = {"bbox": {"x": 10, "y": 10, "width": 50, "height": 50}}

    response = client.post(
        f"/api/samples/{sample_id}/crop",
        headers={"Authorization": f"Bearer {token}"},
        json=crop_data
    )

    assert response.status_code == 201, f"第一次裁剪失败: {response.status_code} - {response.text}"

    crop_region = response.json()
    print(f"✓ 第一次裁剪成功，区域ID: {crop_region['id']}")
    print(f"  裁剪区域: {json.loads(crop_region['bbox'])}")

    # 获取样本详情，验证裁剪区域已保存
    sample_response = client.get(
        f"/api/samples/{sample_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert sample_response.status_code == 200
    sample_detail = sample_response.json()

    assert len(sample_detail['sample_regions']) > 0, "未找到裁剪区域"
    assert sample_detail['sample_regions'][0]['is_auto_detected'] == 0, "应该标记为手动裁剪"
    assert sample_detail['extracted_region_path'] is not None, "未生成裁剪后的图片"

    print(f"✓ 裁剪后的图片路径: {sample_detail['extracted_region_path']}")

    return crop_region['id'], json.loads(crop_region['bbox'])


def test_update_crop_region(token: str, sample_id: int, region_id: int, old_bbox: dict):
    """测试更新裁剪区域（不应创建新记录）"""
    # 第二次裁剪（更新现有的裁剪区域）
    new_crop_data = {"bbox": {"x": 20, "y": 20, "width": 60, "height": 60}}

    response = client.post(
        f"/api/samples/{sample_id}/crop",
        headers={"Authorization": f"Bearer {token}"},
        json=new_crop_data
    )

    assert response.status_code == 201, f"更新裁剪失败: {response.status_code} - {response.text}"

    updated_region = response.json()
    updated_bbox = json.loads(updated_region['bbox'])

    # 验证区域ID相同（更新而不是创建新记录）
    assert updated_region['id'] == region_id, f"应该更新现有记录，而不是创建新记录。旧ID: {region_id}, 新ID: {updated_region['id']}"

    # 验证裁剪区域已更新
    assert updated_bbox['x'] != old_bbox['x'], "裁剪区域应该已更新"
    assert updated_bbox['y'] != old_bbox['y'], "裁剪区域应该已更新"

    print(f"✓ 更新裁剪区域成功（使用现有记录ID: {region_id}）")
    print(f"  新裁剪区域: {updated_bbox}")

    # 获取样本详情，验证只有一个手动裁剪记录
    sample_response = client.get(
        f"/api/samples/{sample_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert sample_response.status_code == 200
    sample_detail = sample_response.json()

    # 统计手动裁剪区域的数量
    manual_regions = [r for r in sample_detail['sample_regions'] if r['is_auto_detected'] == 0]
    assert len(manual_regions) == 1, f"应该只有一个手动裁剪记录，但找到了: {len(manual_regions)}"

    print(f"✓ 验证通过：只有一个手动裁剪记录")


def test_retrieve_saved_crop_area(token: str, sample_id: int):
    """测试重新打开裁剪页面时，能正确显示已保存的裁剪区域"""
    # 获取样本详情
    sample_response = client.get(
        f"/api/samples/{sample_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert sample_response.status_code == 200
    sample_detail = sample_response.json()

    # 查找手动裁剪区域
    manual_regions = [r for r in sample_detail['sample_regions'] if r['is_auto_detected'] == 0]
    assert len(manual_regions) > 0, "未找到手动裁剪区域"

    saved_bbox = json.loads(manual_regions[0]['bbox'])

    print(f"✓ 成功获取已保存的裁剪区域:")
    print(f"  {saved_bbox}")

    return saved_bbox


def test_crop_image_file_exists(token: str, sample_id: int):
    """测试裁剪后的图片文件是否真实存在"""
    sample_response = client.get(
        f"/api/samples/{sample_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert sample_response.status_code == 200
    sample_detail = sample_response.json()

    cropped_path = sample_detail['extracted_region_path']
    assert cropped_path is not None, "裁剪后的图片路径不应为空"

    # 尝试访问裁剪后的图片
    filename = os.path.basename(cropped_path)
    image_response = client.get(f"/uploads/{filename}")

    assert image_response.status_code == 200, f"无法访问裁剪后的图片: {image_response.status_code}"
    assert len(image_response.content) > 0, "裁剪后的图片文件为空"

    print(f"✓ 裁剪后的图片文件可访问: /uploads/{filename}")
    print(f"  文件大小: {len(image_response.content)} bytes")


def cleanup(token: str, sample_id: int):
    """清理测试数据"""
    response = client.delete(
        f"/api/samples/{sample_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 204:
        print(f"✓ 清理完成：已删除测试样本 {sample_id}")


if __name__ == "__main__":
    print("=" * 60)
    print("样本裁剪功能测试")
    print("=" * 60)
    print()

    # 登录
    token = test_login()
    if not token:
        print("✗ 无法登录，跳过测试")
        sys.exit(1)

    print()

    # 上传测试样本
    sample = test_upload_sample(token)
    if not sample:
        print("✗ 无法上传测试样本，跳过测试")
        sys.exit(1)

    sample_id = sample['id']
    print(f"✓ 上传成功，样本ID: {sample_id}")
    print()

    try:
        # 测试裁剪
        region_id, bbox = test_crop_sample(token, sample_id)
        print()

        # 测试更新裁剪区域
        test_update_crop_region(token, sample_id, region_id, bbox)
        print()

        # 测试获取已保存的裁剪区域
        test_retrieve_saved_crop_area(token, sample_id)
        print()

        # 测试裁剪后的图片文件是否存在
        test_crop_image_file_exists(token, sample_id)
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
    finally:
        # 清理测试数据
        print()
        cleanup(token, sample_id)
