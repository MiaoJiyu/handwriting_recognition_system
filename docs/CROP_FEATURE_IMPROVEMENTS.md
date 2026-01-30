# 裁剪功能改进文档

## 修改概述

本次修改实现了以下功能：
1. **显示已保存的裁剪区域**：重新打开裁剪页面时，会显示之前裁剪好的框框
2. **更新现有裁剪区域**：而不是每次都创建新的裁剪记录
3. **重新生成裁剪图片**：每次裁剪后，重新生成裁剪后的图片并保存
4. **画廊视图显示裁剪后的图片**：优先显示裁剪后的图片缩略图

## 修改的文件

### 1. `backend/app/api/samples.py` (line 367-423)

**修改内容：**
- 查找是否存在手动标注的裁剪区域（`is_auto_detected == 0`）
- 如果存在，更新现有的裁剪区域
- 如果不存在，创建新的裁剪区域
- 裁剪后重新生成裁剪后的图片并保存到 `extracted_region_path`
- 将样本状态标记为 `PROCESSED`

**关键代码：**
```python
# 查找是否已存在手动标注的区域
existing_region = db.query(SampleRegion).filter(
    SampleRegion.sample_id == sample_id,
    SampleRegion.is_auto_detected == 0  # 只查找手动标注的
).first()

if existing_region:
    # 更新现有的手动标注区域
    existing_region.bbox = bbox_json
    db.flush()
    region = existing_region
else:
    # 创建新的区域记录
    region = SampleRegion(
        sample_id=sample_id,
        bbox=bbox_json,
        is_auto_detected=0
    )
    db.add(region)

# 裁剪图片并保存
cropped_path = auto_crop_sample_image(sample.image_path, sample_id, crop_data.bbox)
if cropped_path:
    sample.extracted_region_path = cropped_path
```

### 2. `backend/app/utils/image_processor.py`

**修改内容：**
- 修改 `auto_crop_sample_image()` 函数，支持传入裁剪区域
- 添加 `crop_image_by_bbox()` 方法，根据给定的边界框裁剪图像

**关键代码：**
```python
def auto_crop_sample_image(image_path: str, sample_id: int, bbox: Optional[Dict] = None) -> Tuple[Optional[Dict], Optional[str]]:
    """
    裁剪样本图像的便捷函数
    如果提供了bbox，使用给定的裁剪区域；否则自动检测
    返回: (边界框, 裁剪后的图像路径)
    """
    if bbox:
        # 使用给定的裁剪区域
        return image_processor.crop_image_by_bbox(image_path, bbox, sample_id)
    else:
        # 自动检测裁剪区域
        return image_processor.auto_crop_sample(image_path, sample_id)

def crop_image_by_bbox(self, image_path: str, bbox: Dict, sample_id: int) -> Tuple[Optional[Dict], Optional[str]]:
    """
    根据给定的边界框裁剪图像
    返回: (边界框, 裁剪后的图像路径)
    """
    cropped_path = self.crop_image(image_path, bbox)
    return bbox, cropped_path
```

### 3. `frontend/src/pages/SampleList.tsx`

**修改 1：获取已保存的裁剪区域 (line 119-143)**
- 优先查找手动标注的裁剪区域（`is_auto_detected === 0`）
- 如果没有手动标注，使用第一个自动检测的区域
- 返回解析后的裁剪区域对象

**关键代码：**
```typescript
const getSavedCropArea = (): CropArea | null => {
  if (sampleDetail?.sample_regions && sampleDetail.sample_regions.length > 0) {
    try {
      // 优先查找手动标注的区域（is_auto_detected === 0）
      const manualRegion = sampleDetail.sample_regions.find(
        region => region.is_auto_detected === 0
      );
      if (manualRegion) {
        const bbox = JSON.parse(manualRegion.bbox);
        return bbox as CropArea;
      }

      // 如果没有手动标注，使用第一个自动检测的区域
      const autoRegion = sampleDetail.sample_regions[0];
      if (autoRegion) {
        const bbox = JSON.parse(autoRegion.bbox);
        return bbox as CropArea;
      }
    } catch (e) {
      console.error('Failed to parse saved crop area:', e);
    }
  }
  return null;
};
```

**修改 2：更新成功提示 (line 92-106)**
- 提示裁剪区域已保存，裁剪后的图片已更新

**修改 3：画廊视图显示裁剪后的图片 (line 269-327)**
- 优先显示裁剪后的图片（`extracted_region_path`）
- 如果没有裁剪后的图片，显示原始图片
- 在卡片上显示"已裁剪"标签

**关键代码：**
```typescript
// 优先显示裁剪后的图片，否则显示原图
const displayImageUrl = sample.extracted_region_path
  ? getImageUrl(sample.extracted_region_path)
  : (sample.image_url || getImageUrl(sample.image_path));
```

## 功能说明

### 1. 裁剪页面显示已保存的裁剪区域

**工作流程：**
1. 用户点击"裁剪"按钮打开裁剪页面
2. 前端调用 `/api/samples/{sample_id}` 获取样本详情
3. 从样本详情的 `sample_regions` 中查找裁剪区域
4. 优先显示手动标注的裁剪区域（`is_auto_detected === 0`）
5. 如果没有手动标注，显示自动检测的区域
6. 裁剪页面使用 `initialCropArea` 属性显示已保存的裁剪框

### 2. 保存新的裁剪区域

**工作流程：**
1. 用户在裁剪页面调整裁剪框
2. 点击"确认裁剪"按钮
3. 前端调用 `POST /api/samples/{sample_id}/crop` 保存裁剪区域
4. 后端查找是否存在手动标注的裁剪区域
5. 如果存在，更新该区域；否则创建新区域
6. 使用新的裁剪区域重新裁剪图片
7. 将裁剪后的图片保存到 `extracted_region_path`
8. 将样本状态更新为 `PROCESSED`

### 3. 显示裁剪后的图片

**工作流程：**
1. 用户打开样本列表页面（画廊视图）
2. 遍历所有样本
3. 对于每个样本，检查是否有 `extracted_region_path`
4. 如果有裁剪后的图片，优先显示裁剪后的图片
5. 如果没有裁剪后的图片，显示原始图片
6. 在卡片上显示"已裁剪"标签（如果已裁剪）

## 数据流

### 上传样本
```
用户上传图片 → 保存到 uploads/samples/ → 后台自动裁剪 → 保存裁剪区域和裁剪后图片
```

### 手动裁剪
```
打开裁剪页面 → 显示已保存的裁剪框（如有） → 调整裁剪框 → 确认裁剪 → 更新裁剪区域和裁剪后图片
```

### 训练使用
```
查询 samples 表 → 优先使用 extracted_region_path → 如果没有，使用 image_path 和裁剪区域 → 提取特征
```

## 测试建议

### 手动测试步骤

1. **上传样本**
   - 登录系统
   - 上传一张测试图片
   - 等待自动裁剪完成（或手动裁剪）

2. **第一次手动裁剪**
   - 点击样本的"裁剪"按钮
   - 调整裁剪框
   - 点击"确认裁剪"
   - 验证提示"裁剪区域已保存，裁剪后的图片已更新"

3. **第二次打开裁剪页面**
   - 再次点击同一个样本的"裁剪"按钮
   - 验证裁剪框显示的是之前保存的位置（而不是默认位置）
   - 调整裁剪框到新的位置
   - 点击"确认裁剪"
   - 验证裁剪区域已更新（应该只有一个手动裁剪记录）

4. **查看裁剪后的图片**
   - 切换到画廊视图
   - 查看已裁剪的样本卡片
   - 验证显示的是裁剪后的图片（而不是原图）
   - 验证卡片上显示"已裁剪"标签

### 自动测试

运行测试脚本（需要先创建测试账号）：
```bash
cd backend
python tests/test_sample_crop.py
```

## 注意事项

1. **裁剪区域区分**：自动检测的裁剪区域（`is_auto_detected == 1`）和手动标注的裁剪区域（`is_auto_detected == 0`）是分开存储的
2. **优先级**：优先显示和使用手动标注的裁剪区域
3. **文件路径**：裁剪后的图片保存在 `uploads/cropped/` 目录下
4. **训练影响**：训练模块会优先使用 `extracted_region_path`（裁剪后的图片），这确保了训练使用的是用户确认的裁剪区域

## 兼容性

- 向后兼容：旧的样本数据仍然可以正常工作
- 如果样本没有裁剪区域，裁剪页面会显示默认的裁剪框（图片中心）
- 如果样本没有裁剪后的图片，会显示原始图片
