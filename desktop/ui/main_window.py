from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QMessageBox, QProgressBar, QTabWidget,
    QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
import os
import json
from datetime import datetime
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


class DropArea(QLabel):
    """支持拖放的图片显示区域"""
    imageDropped = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(250)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                background: #fafafa;
                border-radius: 8px;
            }
            QLabel:hover {
                border-color: #1890ff;
                background: #e6f7ff;
            }
        """)
        self.setText("拖拽图片到这里\n或点击选择图片")
        self.current_pixmap = None
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if self._is_image_file(file_path):
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        QLabel {
                            border: 2px dashed #1890ff;
                            background: #e6f7ff;
                            border-radius: 8px;
                        }
                    """)
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖出事件"""
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                background: #fafafa;
                border-radius: 8px;
            }
            QLabel:hover {
                border-color: #1890ff;
                background: #e6f7ff;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                background: #fafafa;
                border-radius: 8px;
            }
            QLabel:hover {
                border-color: #1890ff;
                background: #e6f7ff;
            }
        """)
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if self._is_image_file(file_path):
                    self.imageDropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def _is_image_file(self, file_path: str) -> bool:
        """检查是否为图片文件"""
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in valid_extensions
    
    def setImage(self, pixmap: QPixmap):
        """设置图片"""
        self.current_pixmap = pixmap
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
    
    def resizeEvent(self, event):
        """调整大小事件"""
        if self.current_pixmap:
            scaled = self.current_pixmap.scaled(
                event.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)
        super().resizeEvent(event)


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self, history_file: str = "recognition_history.json"):
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self) -> list:
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load history: {e}")
        return []
    
    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def add_record(self, image_path: str, result: dict):
        """添加记录"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "image_path": image_path,
            "image_name": os.path.basename(image_path),
            "is_unknown": result.get("is_unknown", False),
            "confidence": result.get("confidence", 0),
            "top_k": result.get("top_k", [])
        }
        self.history.insert(0, record)
        # 只保留最近100条记录
        self.history = self.history[:100]
        self._save_history()
    
    def get_history(self) -> list:
        """获取历史记录"""
        return self.history
    
    def clear_history(self):
        """清空历史记录"""
        self.history = []
        self._save_history()


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("字迹识别系统 - 桌面版")
        self.setGeometry(100, 100, 1100, 750)
        
        # 历史管理器
        self.history_manager = HistoryManager()
        
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
        
        # 创建Tab组件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 识别Tab
        recognition_tab = self._create_recognition_tab()
        self.tab_widget.addTab(recognition_tab, "识别")
        
        # 历史记录Tab
        history_tab = self._create_history_tab()
        self.tab_widget.addTab(history_tab, "历史记录")
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 支持拖拽图片进行识别")
        
        # 变量
        self.current_image_path = None
        self.recognition_thread = None
    
    def _create_recognition_tab(self) -> QWidget:
        """创建识别Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 选择图片区域
        select_layout = QHBoxLayout()
        
        # 拖放区域
        self.drop_area = DropArea()
        self.drop_area.imageDropped.connect(self.on_image_dropped)
        self.drop_area.mousePressEvent = lambda e: self.select_image() if e.button() == Qt.MouseButton.LeftButton else None
        select_layout.addWidget(self.drop_area, stretch=3)
        
        # 按钮布局
        button_layout = QVBoxLayout()
        self.select_button = QPushButton("选择图片")
        self.select_button.setMinimumHeight(40)
        self.select_button.clicked.connect(self.select_image)
        self.recognize_button = QPushButton("开始识别")
        self.recognize_button.setMinimumHeight(40)
        self.recognize_button.clicked.connect(self.start_recognition)
        self.recognize_button.setEnabled(False)
        self.recognize_button.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:disabled {
                background-color: #d9d9d9;
                color: #999;
            }
        """)
        
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.recognize_button)
        button_layout.addStretch()
        select_layout.addLayout(button_layout)
        
        layout.addLayout(select_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 结果显示
        result_label = QLabel("识别结果:")
        result_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(result_label)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["用户ID", "用户名", "相似度"])
        self.result_table.setColumnWidth(0, 100)
        self.result_table.setColumnWidth(1, 250)
        self.result_table.setColumnWidth(2, 150)
        self.result_table.setAlternatingRowColors(True)
        layout.addWidget(self.result_table)
        
        return tab
    
    def _create_history_tab(self) -> QWidget:
        """创建历史记录Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.refresh_history_btn = QPushButton("刷新")
        self.refresh_history_btn.clicked.connect(self.refresh_history)
        self.clear_history_btn = QPushButton("清空历史")
        self.clear_history_btn.clicked.connect(self.clear_history)
        toolbar.addWidget(self.refresh_history_btn)
        toolbar.addWidget(self.clear_history_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 使用Splitter分割列表和详情
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 历史列表
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        splitter.addWidget(self.history_list)
        
        # 详情面板
        detail_frame = QFrame()
        detail_frame.setFrameShape(QFrame.Shape.StyledPanel)
        detail_layout = QVBoxLayout(detail_frame)
        
        self.history_image_label = QLabel("选择一条记录查看详情")
        self.history_image_label.setMinimumHeight(200)
        self.history_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_image_label.setStyleSheet("background: #f5f5f5; border: 1px solid #ddd;")
        detail_layout.addWidget(self.history_image_label)
        
        self.history_detail_table = QTableWidget()
        self.history_detail_table.setColumnCount(3)
        self.history_detail_table.setHorizontalHeaderLabels(["用户ID", "用户名", "相似度"])
        detail_layout.addWidget(self.history_detail_table)
        
        splitter.addWidget(detail_frame)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # 加载历史记录
        self.refresh_history()
        
        return tab
    
    def on_image_dropped(self, file_path: str):
        """处理拖放的图片"""
        self.load_image(file_path)
    
    def load_image(self, file_path: str):
        """加载图片"""
        if file_path and os.path.exists(file_path):
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            self.drop_area.setImage(pixmap)
            self.recognize_button.setEnabled(True)
            self.statusBar().showMessage(f"已选择: {os.path.basename(file_path)}")
    
    def select_image(self):
        """选择图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        
        if file_path:
            self.load_image(file_path)
    
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
        
        # 保存到历史记录
        self.history_manager.add_record(self.current_image_path, result)
        
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
    
    def refresh_history(self):
        """刷新历史记录"""
        self.history_list.clear()
        history = self.history_manager.get_history()
        
        for record in history:
            timestamp = datetime.fromisoformat(record["timestamp"])
            display_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            if record.get("is_unknown"):
                result_text = "未识别"
            else:
                confidence = record.get("confidence", 0) * 100
                result_text = f"置信度: {confidence:.1f}%"
            
            item_text = f"{display_time}\n{record['image_name']}\n{result_text}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.history_list.addItem(item)
    
    def on_history_item_clicked(self, item: QListWidgetItem):
        """点击历史记录项"""
        record = item.data(Qt.ItemDataRole.UserRole)
        
        # 显示图片
        image_path = record.get("image_path", "")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(
                self.history_image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.history_image_label.setPixmap(scaled)
        else:
            self.history_image_label.setText(f"图片不存在:\n{image_path}")
        
        # 显示识别结果
        top_k = record.get("top_k", [])
        self.history_detail_table.setRowCount(len(top_k))
        
        for i, item_data in enumerate(top_k):
            self.history_detail_table.setItem(i, 0, QTableWidgetItem(str(item_data.get("user_id", ""))))
            self.history_detail_table.setItem(i, 1, QTableWidgetItem(item_data.get("username", "")))
            self.history_detail_table.setItem(i, 2, QTableWidgetItem(f"{item_data.get('score', 0) * 100:.2f}%"))
    
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空所有历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_history()
            self.refresh_history()
            self.history_image_label.setText("选择一条记录查看详情")
            self.history_detail_table.setRowCount(0)
            self.statusBar().showMessage("历史记录已清空")
