from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
import os
from api_client.grpc_client import InferenceClient


class RecognitionThread(QThread):
    """识别线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, image_path: str):
        super().__init__()
        self.image_path = image_path
    
    def run(self):
        try:
            client = InferenceClient()
            result = client.recognize(self.image_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("字迹识别系统 - 桌面版")
        self.setGeometry(100, 100, 1000, 700)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 标题
        title_label = QLabel("字迹识别系统")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 选择图片区域
        select_layout = QHBoxLayout()
        self.image_label = QLabel("未选择图片")
        self.image_label.setMinimumHeight(200)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        select_layout.addWidget(self.image_label)
        
        button_layout = QVBoxLayout()
        self.select_button = QPushButton("选择图片")
        self.select_button.clicked.connect(self.select_image)
        self.recognize_button = QPushButton("开始识别")
        self.recognize_button.clicked.connect(self.start_recognition)
        self.recognize_button.setEnabled(False)
        
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.recognize_button)
        button_layout.addStretch()
        select_layout.addLayout(button_layout)
        
        main_layout.addLayout(select_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 结果显示
        result_label = QLabel("识别结果:")
        result_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(result_label)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["用户ID", "用户名", "相似度"])
        self.result_table.setColumnWidth(0, 100)
        self.result_table.setColumnWidth(1, 200)
        self.result_table.setColumnWidth(2, 150)
        main_layout.addWidget(self.result_table)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 变量
        self.current_image_path = None
        self.recognition_thread = None
    
    def select_image(self):
        """选择图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.recognize_button.setEnabled(True)
            self.statusBar().showMessage(f"已选择: {os.path.basename(file_path)}")
    
    def start_recognition(self):
        """开始识别"""
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return
        
        # 禁用按钮
        self.select_button.setEnabled(False)
        self.recognize_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 启动识别线程
        self.recognition_thread = RecognitionThread(self.current_image_path)
        self.recognition_thread.finished.connect(self.on_recognition_finished)
        self.recognition_thread.error.connect(self.on_recognition_error)
        self.recognition_thread.start()
        
        self.statusBar().showMessage("识别中...")
    
    def on_recognition_finished(self, result: dict):
        """识别完成"""
        # 恢复按钮
        self.select_button.setEnabled(True)
        self.recognize_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示结果
        self.result_table.setRowCount(len(result.get("top_k", [])))
        
        for i, item in enumerate(result.get("top_k", [])):
            self.result_table.setItem(i, 0, QTableWidgetItem(str(item.get("user_id", ""))))
            self.result_table.setItem(i, 1, QTableWidgetItem(item.get("username", "")))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{item.get('score', 0) * 100:.2f}%"))
        
        # 显示消息
        if result.get("is_unknown", False):
            QMessageBox.information(self, "识别结果", "未识别出匹配的用户")
        else:
            confidence = result.get("confidence", 0) * 100
            QMessageBox.information(
                self,
                "识别结果",
                f"识别完成！\n置信度: {confidence:.2f}%"
            )
        
        self.statusBar().showMessage("识别完成")
    
    def on_recognition_error(self, error_msg: str):
        """识别错误"""
        # 恢复按钮
        self.select_button.setEnabled(True)
        self.recognize_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "错误", f"识别失败: {error_msg}")
        self.statusBar().showMessage("识别失败")
