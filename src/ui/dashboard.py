from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal

class TileButton(QtWidgets.QFrame):
    clicked = pyqtSignal()

    def __init__(self, title, icon_path, color_gradient, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 200)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("TileButton")
        self.setStyleSheet(f"""
            #TileButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {color_gradient});
                border-radius: 15px;
                border: 2px solid rgba(255, 255, 255, 20);
            }}
            #TileButton:hover {{
                border: 2px solid rgba(255, 255, 255, 80);
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {color_gradient.replace('0.6', '0.8')});
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        # In a real app we'd load icons, here we use text/placeholders for now
        self.icon_label.setText(icon_path) 
        self.icon_label.setStyleSheet("font-size: 60px; color: white;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white; text-transform: uppercase;")
        self.title_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)

    def mousePressEvent(self, event):
        self.clicked.emit()

class DashboardView(QWidget):
    tile_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(30)

        # Header
        header_layout = QHBoxLayout()
        self.logo_label = QLabel("IPTV SMARTERS PRO")
        self.logo_label.setStyleSheet("font-size: 32px; font-weight: bold; color: white;")
        header_layout.addWidget(self.logo_label)
        header_layout.addStretch()
        
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("font-size: 18px; color: white;")
        header_layout.addWidget(self.time_label)
        
        main_layout.addLayout(header_layout)

        # Tiles Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # Define Tiles based on example.jpg
        # Live TV (Large)
        self.live_tile = TileButton("Live TV", "📺", "stop:0 #00d2ff, stop:1 #3a7bd5")
        self.live_tile.setFixedSize(300, 420)
        self.live_tile.clicked.connect(lambda: self.tile_clicked.emit("LIVE"))
        grid_layout.addWidget(self.live_tile, 0, 0, 2, 1)

        # Movies
        self.movies_tile = TileButton("Movies", "🎬", "stop:0 #f85032, stop:1 #e73827")
        self.movies_tile.clicked.connect(lambda: self.tile_clicked.emit("Movies"))
        grid_layout.addWidget(self.movies_tile, 0, 1)

        # Series
        self.series_tile = TileButton("Series", "🎞️", "stop:0 #a18cd1, stop:1 #fbc2eb")
        self.series_tile.clicked.connect(lambda: self.tile_clicked.emit("Series"))
        grid_layout.addWidget(self.series_tile, 0, 2)


        main_layout.addLayout(grid_layout)
        main_layout.addStretch()

        # Footer
        footer_layout = QHBoxLayout()
        self.expiration_label = QLabel("Expiration: Unlimited")
        self.expiration_label.setStyleSheet("color: rgba(255,255,255,0.7);")
        footer_layout.addWidget(self.expiration_label)
        footer_layout.addStretch()
        self.user_label = QLabel("Logged in: Guest")
        self.user_label.setStyleSheet("color: rgba(255,255,255,0.7);")
        footer_layout.addWidget(self.user_label)
        main_layout.addLayout(footer_layout)

        # Timer for clock
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

    def update_time(self):
        from datetime import datetime
        self.time_label.setText(datetime.now().strftime("%H:%M  %b %d, %Y"))
        
    def update_user_info(self, username, expiry):
        self.user_label.setText(f"Logged in: {username}")
        self.expiration_label.setText(f"Expiration: {expiry}")
