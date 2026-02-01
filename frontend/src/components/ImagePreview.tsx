import React from 'react';
import { Modal, Image } from 'antd';

interface ImagePreviewProps {
  visible: boolean;
  imageUrl: string;
  imageTitle?: string;
  onClose: () => void;
}

const ImagePreview: React.FC<ImagePreviewProps> = ({
  visible,
  imageUrl,
  imageTitle = '图片预览',
  onClose,
}) => {
  return (
    <Modal
      open={visible}
      title={imageTitle}
      onCancel={onClose}
      footer={null}
      width="80%"
      centered
      style={{ top: 20 }}
    >
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Image
          src={imageUrl}
          alt={imageTitle}
          style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain' }}
          preview={false}
          fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect width='100%25' height='100%25' fill='%23f5f5f5'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999' font-size='16'%3EImage%20Load%20Error%3C/text%3E%3C/svg%3E"
        />
      </div>
    </Modal>
  );
};

export default ImagePreview;
