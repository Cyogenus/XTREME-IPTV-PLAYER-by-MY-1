from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
                             QLineEdit, QHBoxLayout, QPushButton, QLabel, 
                             QScrollArea, QFrame, QGridLayout, QListView)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QByteArray, QThreadPool, QTimer
from PyQt5.QtGui import QPixmap
from src.ui.models import ContentModel
from src.ui.delegates import ContentDelegate


class ContentListView(QWidget):
    category_clicked = pyqtSignal(dict)
    item_clicked = pyqtSignal(dict)
    back_clicked = pyqtSignal()

    def __init__(self, tab_name, parent=None):
        super().__init__(parent)
        self.tab_name = tab_name
        self.model = ContentModel()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top Bar
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background-color: rgba(15, 23, 42, 0.8); border-bottom: 1px solid rgba(255,255,255,0.1);")
        top_layout = QHBoxLayout(top_bar)
        
        self.back_btn = QPushButton("← BACK")
        self.back_btn.setObjectName("BackButton")
        self.back_btn.setFixedWidth(100)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        top_layout.addWidget(self.back_btn)
        
        self.title_label = QLabel(self.tab_name)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white; margin-left: 20px;")
        top_layout.addWidget(self.title_label)
        
        top_layout.addStretch()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(f"Search in {self.tab_name}...")
        self.search_bar.setFixedWidth(300)
        top_layout.addWidget(self.search_bar)
        
        main_layout.addWidget(top_bar)
        
        # Content Split Layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        
        # Left Side (1/3) - Categories
        self.cat_list = QListWidget()
        self.cat_list.setFixedWidth(300)
        self.cat_list.setObjectName("CategoryList")
        self.cat_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(30, 41, 59, 0.5);
                border: none;
                border-right: 1px solid rgba(255,255,255,0.1);
            }
            QListWidget::item {
                padding: 15px;
                color: #94a3b8;
                border-bottom: 1px solid rgba(255,255,255,0.03);
            }
            QListWidget::item:selected {
                background-color: rgba(59, 130, 246, 0.2);
                color: white;
                border-left: 4px solid #3b82f6;
            }
        """)
        self.cat_list.itemClicked.connect(self.on_cat_clicked)
        content_layout.addWidget(self.cat_list)
        
        # Right Side (2/3) - Content Grid (Virtualized via QListView)
        self.list_view = QListView()
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setMovement(QListView.Static)
        self.list_view.setSpacing(10)
        self.list_view.setWrapping(True)
        self.list_view.setWordWrap(True)
        self.list_view.setStyleSheet("background-color: transparent; border: none;")
        
        self.list_view.setModel(self.model)
        self.delegate = ContentDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        
        self.list_view.clicked.connect(self.on_item_clicked)
        content_layout.addWidget(self.list_view)
        
        main_layout.addLayout(content_layout)

    def set_categories(self, categories):
        self.cat_list.clear()
        for cat in categories:
            item = QListWidgetItem(cat.get('category_name', 'Unknown'))
            item.setData(Qt.UserRole, cat)
            self.cat_list.addItem(item)

    def set_items(self, items):
        self.model.set_items(items)

    def on_item_clicked(self, index):
        data = index.data(Qt.UserRole)
        if data:
            self.item_clicked.emit(data)

    def on_cat_clicked(self, item):
        data = item.data(Qt.UserRole)
        self.category_clicked.emit(data)
