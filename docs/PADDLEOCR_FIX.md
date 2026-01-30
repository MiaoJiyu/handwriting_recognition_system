# PaddleOCR兼容性修复说明

## 问题描述
使用PaddleOCR 2.7.0 + PaddlePaddle 3.0.0时出现以下错误：
```
文本检测失败: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
```

## 原因
这是PaddleOCR库与特定PaddlePaddle版本之间的兼容性问题。PaddlePaddle 3.0.0引入了新的PIR（Paddle Intermediate Representation）转换系统，但PaddleOCR 2.7.0可能与某些PIR属性不兼容。

## 解决方案

### 方案1：降级到已知兼容版本（推荐）

修改 `backend/requirements.txt` 中的PaddlePaddle版本：

```bash
# 修改前
paddlepaddle>=3.0.0

# 修改后
paddlepaddle==2.5.2
```

然后重新安装依赖：

```bash
cd backend
pip install --upgrade paddlepaddle==2.5.2
```

### 方案2：使用代码中的回退机制

当前代码已经实现了回退机制，当PaddleOCR不可用或失败时，会自动使用OpenCV进行文本区域检测：

- **优先使用PaddleOCR**：准确的文本检测
- **失败时自动切换到OpenCV**：使用轮廓检测进行文本区域识别
- **无需修改配置**：自动降级，不影响正常使用

## 降级到兼容版本的步骤

### 1. 卸载当前版本
```bash
pip uninstall paddlepaddle paddleocr
```

### 2. 安装兼容版本
```bash
pip install paddlepaddle==2.5.2 paddleocr==2.7.3
```

### 3. 验证安装
```bash
python -c "import paddleocr; import paddle; print('PaddleOCR版本:', paddleocr.__version__); print('PaddlePaddle版本:', paddle.__version__)"
```

## 测试自动裁剪功能

安装兼容版本后，重启后端服务：

```bash
cd backend
# 如果使用virtualenv
source venv/bin/activate

# 或使用运行脚本
./run_server.sh
```

上传新的样本图片，检查日志输出：

**成功情况**：
```
PaddleOCR初始化成功
开始自动裁剪样本 18
检测到文本区域，共5个候选框
样本 18 自动裁剪成功
```

**回退情况**（如果PaddleOCR仍然失败）：
```
PaddleOCR初始化失败: [错误信息]
将使用OpenCV回退方案进行文本检测
使用OpenCV进行文本检测
检测到文本区域，共3个候选框
样本 18 自动裁剪成功
```

## OpenCV回退方案说明

如果PaddleOCR完全不可用，系统会使用OpenCV进行文本检测：

1. **图像预处理**：灰度化 + 二值化
2. **轮廓检测**：查找文本候选区域
3. **区域过滤**：过滤太小的噪声区域（< 50x50像素）
4. **边界框生成**：为每个区域生成(x, y, width, height)

虽然OpenCV的准确度不如PaddleOCR，但能够：
- ✅ 正常处理样本上传
- ✅ 提供基本的自动裁剪功能
- ✅ 不阻塞整个系统流程

## 推荐配置

对于生产环境，建议使用以下配置：

```bash
# requirements.txt
paddlepaddle==2.5.2
paddleocr==2.7.3
opencv-python>=4.8.1.78
```

这个配置组合经过测试，能够正常工作且兼容性良好。
