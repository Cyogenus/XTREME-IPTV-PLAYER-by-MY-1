from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                             QLabel, QComboBox, QHBoxLayout, QFrame, QListWidget, 
                             QListWidgetItem, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal

class LoginView(QWidget):
    login_xtream = pyqtSignal(str, str, str, str) # name, server, user, pass
    login_m3u = pyqtSignal(str, str) # name, url/path
    profile_selected = pyqtSignal(dict)
    delete_profile_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(40)
        
        # Left: Saved Profiles (1/3)
        profile_frame = QFrame()
        profile_frame.setObjectName("ProfileFrame")
        profile_frame.setFixedWidth(300)
        profile_frame.setStyleSheet("""
            #ProfileFrame {
                background-color: rgba(30, 41, 59, 0.7);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        profile_layout = QVBoxLayout(profile_frame)
        profile_layout.addWidget(QLabel("SAVED PROFILES"))
        
        self.profile_list = QListWidget()
        self.profile_list.setStyleSheet("background: transparent; border: none; color: white;")
        self.profile_list.itemClicked.connect(self.on_profile_clicked)
        profile_layout.addWidget(self.profile_list)
        
        self.delete_profile_btn = QPushButton("Delete Selected")
        self.delete_profile_btn.clicked.connect(self.on_delete_profile)
        profile_layout.addWidget(self.delete_profile_btn)
        
        layout.addWidget(profile_frame)
        
        # Right: Login Form (2/3)
        container = QFrame()
        container.setObjectName("LoginContainer")
        container.setStyleSheet("""
            #LoginContainer {
                background-color: rgba(30, 41, 59, 0.95);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        title = QLabel("CONNECT NEW")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)
        
        # Profile Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile Name (e.g. My Server)")
        container_layout.addWidget(self.name_input)

        # Mode Selection
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Xtream Codes API", "M3U Playlist URL"])
        self.mode_selector.currentIndexChanged.connect(self.toggle_mode)
        container_layout.addWidget(self.mode_selector)

        # Xtream Fields
        self.xtream_widget = QWidget()
        xtream_layout = QVBoxLayout(self.xtream_widget)
        xtream_layout.setContentsMargins(0, 0, 0, 0)
        
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("Server URL (e.g. http://example.com:8080)")
        xtream_layout.addWidget(self.server_input)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        xtream_layout.addWidget(self.user_input)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        xtream_layout.addWidget(self.pass_input)
        
        container_layout.addWidget(self.xtream_widget)

        # M3U Fields
        self.m3u_widget = QWidget()
        m3u_layout = QVBoxLayout(self.m3u_widget)
        m3u_layout.setContentsMargins(0, 0, 0, 0)
        
        self.m3u_input = QLineEdit()
        self.m3u_input.setPlaceholderText("M3U Playlist URL")
        m3u_layout.addWidget(self.m3u_input)
        
        container_layout.addWidget(self.m3u_widget)
        self.m3u_widget.hide()

        self.remember_cb = QCheckBox("Save these credentials")
        self.remember_cb.setStyleSheet("color: white;")
        self.remember_cb.setChecked(True)
        container_layout.addWidget(self.remember_cb)

        self.login_btn = QPushButton("CONNECT")
        self.login_btn.setFixedHeight(50)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        container_layout.addWidget(self.login_btn)

        layout.addWidget(container)

    def set_profiles(self, profiles):
        self.profile_list.clear()
        for p in profiles:
            item = QListWidgetItem(p.get('name', 'Unnamed'))
            item.setData(Qt.UserRole, p)
            self.profile_list.addItem(item)

    def toggle_mode(self, index):
        self.xtream_widget.setVisible(index == 0)
        self.m3u_widget.setVisible(index == 1)

    def on_profile_clicked(self, item):
        profile = item.data(Qt.UserRole)
        self.profile_selected.emit(profile)

    def on_delete_profile(self):
        item = self.profile_list.currentItem()
        if item:
            profile = item.data(Qt.UserRole)
            self.delete_profile_requested.emit(profile.get('id'))

    def handle_login(self):
        name = self.name_input.text().strip() or "Default"
        save = self.remember_cb.isChecked()
        
        if self.mode_selector.currentIndex() == 0:
            server = self.server_input.text().strip()
            user = self.user_input.text().strip()
            password = self.pass_input.text().strip()
            if server and user and password:
                # If save is true, we should probably tell MainWindow to save it
                self.login_xtream.emit(name, server, user, password)
        else:
            url = self.m3u_input.text().strip()
            if url:
                self.login_m3u.emit(name, url)
