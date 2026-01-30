import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Modal, Button, Space, Slider, Typography } from 'antd';
import { ZoomInOutlined, ZoomOutOutlined, UndoOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface ImageCropperProps {
  visible: boolean;
  imageUrl: string;
  onCrop: (cropArea: CropArea) => void;
  onCancel: () => void;
  title?: string;
  initialCropArea?: CropArea;  // 新增：初始裁剪区域
}

const ImageCropper: React.FC<ImageCropperProps> = ({
  visible,
  imageUrl,
  onCrop,
  onCancel,
  title = '裁剪图片',
  initialCropArea,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [scale, setScale] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string>('');
  const [cropArea, setCropArea] = useState<CropArea>({ x: 50, y: 50, width: 200, height: 150 });
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageOffset, setImageOffset] = useState({ x: 0, y: 0 });

  // 加载图片
  useEffect(() => {
    if (visible && imageUrl) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        setImage(img);

        // 如果提供了初始裁剪区域，使用它；否则初始化为图片中心
        if (initialCropArea) {
          setCropArea(initialCropArea);
        } else {
          const cropWidth = Math.min(img.width * 0.5, 300);
          const cropHeight = Math.min(img.height * 0.5, 200);
          setCropArea({
            x: (img.width - cropWidth) / 2,
            y: (img.height - cropHeight) / 2,
            width: cropWidth,
            height: cropHeight,
          });
        }

        // 计算合适的缩放比例
        if (containerRef.current) {
          const containerWidth = containerRef.current.clientWidth - 40;
          const containerHeight = 400;
          const scaleX = containerWidth / img.width;
          const scaleY = containerHeight / img.height;
          setScale(Math.min(scaleX, scaleY, 1));
        }
      };
      img.src = imageUrl;
    }
  }, [visible, imageUrl, initialCropArea]);

  // 绘制画布
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !image) return;

    // 设置画布大小
    canvas.width = image.width * scale;
    canvas.height = image.height * scale;

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 绘制图片
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

    // 绘制半透明遮罩
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 清除裁剪区域的遮罩
    const scaledCrop = {
      x: cropArea.x * scale,
      y: cropArea.y * scale,
      width: cropArea.width * scale,
      height: cropArea.height * scale,
    };
    ctx.clearRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);
    ctx.drawImage(
      image,
      cropArea.x,
      cropArea.y,
      cropArea.width,
      cropArea.height,
      scaledCrop.x,
      scaledCrop.y,
      scaledCrop.width,
      scaledCrop.height
    );

    // 绘制裁剪框边框
    ctx.strokeStyle = '#1890ff';
    ctx.lineWidth = 2;
    ctx.strokeRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);

    // 绘制调整手柄
    const handleSize = 8;
    ctx.fillStyle = '#1890ff';
    const handles = [
      { x: scaledCrop.x, y: scaledCrop.y }, // top-left
      { x: scaledCrop.x + scaledCrop.width / 2, y: scaledCrop.y }, // top-center
      { x: scaledCrop.x + scaledCrop.width, y: scaledCrop.y }, // top-right
      { x: scaledCrop.x + scaledCrop.width, y: scaledCrop.y + scaledCrop.height / 2 }, // right-center
      { x: scaledCrop.x + scaledCrop.width, y: scaledCrop.y + scaledCrop.height }, // bottom-right
      { x: scaledCrop.x + scaledCrop.width / 2, y: scaledCrop.y + scaledCrop.height }, // bottom-center
      { x: scaledCrop.x, y: scaledCrop.y + scaledCrop.height }, // bottom-left
      { x: scaledCrop.x, y: scaledCrop.y + scaledCrop.height / 2 }, // left-center
    ];

    handles.forEach((handle) => {
      ctx.fillRect(handle.x - handleSize / 2, handle.y - handleSize / 2, handleSize, handleSize);
    });

    // 绘制网格线（三等分线）
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.lineWidth = 1;
    // 垂直线
    ctx.beginPath();
    ctx.moveTo(scaledCrop.x + scaledCrop.width / 3, scaledCrop.y);
    ctx.lineTo(scaledCrop.x + scaledCrop.width / 3, scaledCrop.y + scaledCrop.height);
    ctx.moveTo(scaledCrop.x + (scaledCrop.width * 2) / 3, scaledCrop.y);
    ctx.lineTo(scaledCrop.x + (scaledCrop.width * 2) / 3, scaledCrop.y + scaledCrop.height);
    // 水平线
    ctx.moveTo(scaledCrop.x, scaledCrop.y + scaledCrop.height / 3);
    ctx.lineTo(scaledCrop.x + scaledCrop.width, scaledCrop.y + scaledCrop.height / 3);
    ctx.moveTo(scaledCrop.x, scaledCrop.y + (scaledCrop.height * 2) / 3);
    ctx.lineTo(scaledCrop.x + scaledCrop.width, scaledCrop.y + (scaledCrop.height * 2) / 3);
    ctx.stroke();
  }, [image, scale, cropArea]);

  useEffect(() => {
    draw();
  }, [draw]);

  // 获取鼠标在画布上的位置
  const getMousePos = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / scale,
      y: (e.clientY - rect.top) / scale,
    };
  };

  // 检测鼠标是否在调整手柄上
  const getResizeHandle = (pos: { x: number; y: number }) => {
    const handleSize = 10 / scale;
    const { x, y, width, height } = cropArea;

    if (Math.abs(pos.x - x) < handleSize && Math.abs(pos.y - y) < handleSize) return 'nw';
    if (Math.abs(pos.x - (x + width)) < handleSize && Math.abs(pos.y - y) < handleSize) return 'ne';
    if (Math.abs(pos.x - (x + width)) < handleSize && Math.abs(pos.y - (y + height)) < handleSize) return 'se';
    if (Math.abs(pos.x - x) < handleSize && Math.abs(pos.y - (y + height)) < handleSize) return 'sw';
    if (Math.abs(pos.x - (x + width / 2)) < handleSize && Math.abs(pos.y - y) < handleSize) return 'n';
    if (Math.abs(pos.x - (x + width)) < handleSize && Math.abs(pos.y - (y + height / 2)) < handleSize) return 'e';
    if (Math.abs(pos.x - (x + width / 2)) < handleSize && Math.abs(pos.y - (y + height)) < handleSize) return 's';
    if (Math.abs(pos.x - x) < handleSize && Math.abs(pos.y - (y + height / 2)) < handleSize) return 'w';

    return '';
  };

  // 检测鼠标是否在裁剪框内
  const isInsideCropArea = (pos: { x: number; y: number }) => {
    return (
      pos.x >= cropArea.x &&
      pos.x <= cropArea.x + cropArea.width &&
      pos.y >= cropArea.y &&
      pos.y <= cropArea.y + cropArea.height
    );
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getMousePos(e);
    const handle = getResizeHandle(pos);

    if (handle) {
      setIsResizing(true);
      setResizeHandle(handle);
    } else if (isInsideCropArea(pos)) {
      setIsDragging(true);
    }
    setDragStart(pos);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getMousePos(e);

    // 更新光标样式
    const canvas = canvasRef.current;
    if (canvas) {
      const handle = getResizeHandle(pos);
      if (handle) {
        const cursors: { [key: string]: string } = {
          nw: 'nw-resize',
          ne: 'ne-resize',
          se: 'se-resize',
          sw: 'sw-resize',
          n: 'n-resize',
          s: 's-resize',
          e: 'e-resize',
          w: 'w-resize',
        };
        canvas.style.cursor = cursors[handle] || 'default';
      } else if (isInsideCropArea(pos)) {
        canvas.style.cursor = 'move';
      } else {
        canvas.style.cursor = 'default';
      }
    }

    if (!isDragging && !isResizing) return;
    if (!image) return;

    const dx = pos.x - dragStart.x;
    const dy = pos.y - dragStart.y;

    if (isDragging) {
      // 移动裁剪框
      setCropArea((prev) => {
        let newX = prev.x + dx;
        let newY = prev.y + dy;
        // 边界检查
        newX = Math.max(0, Math.min(newX, image.width - prev.width));
        newY = Math.max(0, Math.min(newY, image.height - prev.height));
        return { ...prev, x: newX, y: newY };
      });
    } else if (isResizing) {
      // 调整裁剪框大小
      setCropArea((prev) => {
        let { x, y, width, height } = prev;
        const minSize = 20;

        switch (resizeHandle) {
          case 'nw':
            x += dx;
            y += dy;
            width -= dx;
            height -= dy;
            break;
          case 'ne':
            y += dy;
            width += dx;
            height -= dy;
            break;
          case 'se':
            width += dx;
            height += dy;
            break;
          case 'sw':
            x += dx;
            width -= dx;
            height += dy;
            break;
          case 'n':
            y += dy;
            height -= dy;
            break;
          case 's':
            height += dy;
            break;
          case 'e':
            width += dx;
            break;
          case 'w':
            x += dx;
            width -= dx;
            break;
        }

        // 确保最小尺寸
        if (width < minSize) {
          if (resizeHandle.includes('w')) x = prev.x + prev.width - minSize;
          width = minSize;
        }
        if (height < minSize) {
          if (resizeHandle.includes('n')) y = prev.y + prev.height - minSize;
          height = minSize;
        }

        // 边界检查
        x = Math.max(0, x);
        y = Math.max(0, y);
        if (x + width > image.width) width = image.width - x;
        if (y + height > image.height) height = image.height - y;

        return { x, y, width, height };
      });
    }

    setDragStart(pos);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeHandle('');
  };

  const handleConfirm = () => {
    // 返回实际图片坐标（未缩放的）
    onCrop({
      x: Math.round(cropArea.x),
      y: Math.round(cropArea.y),
      width: Math.round(cropArea.width),
      height: Math.round(cropArea.height),
    });
  };

  const handleReset = () => {
    if (image) {
      const cropWidth = Math.min(image.width * 0.5, 300);
      const cropHeight = Math.min(image.height * 0.5, 200);
      setCropArea({
        x: (image.width - cropWidth) / 2,
        y: (image.height - cropHeight) / 2,
        width: cropWidth,
        height: cropHeight,
      });
    }
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="reset" icon={<UndoOutlined />} onClick={handleReset}>
          重置
        </Button>,
        <Button key="confirm" type="primary" onClick={handleConfirm}>
          确认裁剪
        </Button>,
      ]}
    >
      <div ref={containerRef} style={{ padding: '20px 0' }}>
        <div style={{ marginBottom: 16 }}>
          <Space align="center">
            <ZoomOutOutlined />
            <Slider
              min={0.1}
              max={2}
              step={0.1}
              value={scale}
              onChange={setScale}
              style={{ width: 150 }}
            />
            <ZoomInOutlined />
            <Text type="secondary" style={{ marginLeft: 16 }}>
              裁剪区域: {Math.round(cropArea.width)} x {Math.round(cropArea.height)} px
            </Text>
          </Space>
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            overflow: 'auto',
            maxHeight: 450,
            backgroundColor: '#f0f0f0',
            borderRadius: 8,
            padding: 10,
          }}
        >
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{ display: image ? 'block' : 'none' }}
          />
          {!image && (
            <div style={{ padding: 50, color: '#999' }}>加载图片中...</div>
          )}
        </div>
        <div style={{ marginTop: 12, color: '#666', fontSize: 12 }}>
          提示：拖拽裁剪框移动位置，拖拽四角或边缘调整大小
        </div>
      </div>
    </Modal>
  );
};

export default ImageCropper;
