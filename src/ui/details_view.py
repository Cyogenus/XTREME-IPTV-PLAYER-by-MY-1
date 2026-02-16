from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QByteArray, QThreadPool
from PyQt5.QtGui import QPixmap
from src.utils.image_loader import ImageLoader

class DetailsView(QWidget):
    back_clicked = pyqtSignal()
    play_clicked = pyqtSignal(dict) # Data contains url or info to play

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loader = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Back Button
        self.back_btn = QPushButton("← BACK")
        self.back_btn.setObjectName("BackButton")
        self.back_btn.setFixedWidth(100)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self.back_btn)
        
        # Main Content Area
        main_content = QHBoxLayout()
        main_content.setSpacing(40)
        
        # Left: Poster
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(300, 450)
        self.poster_label.setStyleSheet("background-color: #1e293b; border-radius: 15px;")
        main_content.addWidget(self.poster_label)
        
        # Right: Info
        info_layout = QVBoxLayout()
        
        self.title_label = QLabel("Title")
        self.title_label.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        info_layout.addWidget(self.title_label)
        
        self.meta_label = QLabel("Year | Duration | Rating")
        self.meta_label.setStyleSheet("font-size: 16px; color: #94a3b8;")
        info_layout.addWidget(self.meta_label)
        
        self.plot_label = QLabel("Description goes here...")
        self.plot_label.setStyleSheet("font-size: 16px; color: #cbd5e1; margin-top: 20px;")
        self.plot_label.setWordWrap(True)
        info_layout.addWidget(self.plot_label)
        
        info_layout.addStretch()
        
        self.play_btn = QPushButton("PLAY NOW")
        self.play_btn.setFixedSize(200, 50)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.play_btn.clicked.connect(self.on_play_clicked)
        info_layout.addWidget(self.play_btn)
        
        main_content.addLayout(info_layout)
        layout.addLayout(main_content)
        
        # Seasons/Episodes Area (Hidden by default)
        self.series_container = QWidget()
        series_layout = QVBoxLayout(self.series_container)
        
        self.season_list = QListWidget()
        self.season_list.setFixedHeight(100)
        self.season_list.setFlow(QListWidget.LeftToRight)
        self.season_list.setObjectName("SeasonList")
        series_layout.addWidget(QLabel("SEASONS"))
        series_layout.addWidget(self.season_list)
        
        self.episode_list = QListWidget()
        self.episode_list.setObjectName("EpisodeList")
        self.episode_list.itemDoubleClicked.connect(self.on_episode_double_clicked)
        series_layout.addWidget(QLabel("EPISODES"))
        series_layout.addWidget(self.episode_list)
        
        layout.addWidget(self.series_container)
        self.series_container.hide()

    def set_movie_data(self, data):
        self.current_data = data
        info = data.get('info', {})
        
        self.title_label.setText(info.get('name', 'Unknown'))
        self.meta_label.setText(f"{info.get('releasedate', 'N/A')} | {info.get('duration', 'N/A')} | ⭐ {info.get('rating', 'N/A')}")
        self.plot_label.setText(info.get('plot', 'No description available.'))
        
        img_url = (info.get('movie_image') or 
                   info.get('cover_big') or 
                   info.get('movie_icon') or 
                   info.get('stream_icon') or
                   info.get('poster'))
        if img_url:
            self.load_image(img_url)
        else:
            self.poster_label.clear()

        self.series_container.hide()
        self.play_btn.show()

    def set_series_data(self, data):
        self.current_data = data
        info = data.get('info', {})
        episodes = data.get('episodes', {}) 
        
        self.title_label.setText(info.get('name', 'Unknown'))
        self.meta_label.setText(f"{info.get('releaseDate', 'N/A')} | ⭐ {info.get('rating', 'N/A')}")
        self.plot_label.setText(info.get('plot', 'No description available.'))
        
        img_url = (info.get('cover') or 
                   info.get('series_cover') or 
                   info.get('stream_icon') or
                   info.get('icon'))
        if img_url:
            self.load_image(img_url)
        else:
            self.poster_label.clear()

        self.play_btn.hide()
        self.series_container.show()
        
        self.season_list.clear() # clear list first
        self.episode_list.clear()
        
        # Populate seasons
        seasons = sorted([int(k) for k in episodes.keys()])
        for season_num in seasons:
            item = QListWidgetItem(f"Season {season_num}")
            item.setData(Qt.UserRole, str(season_num))
            self.season_list.addItem(item)
            
        self.episodes_map = episodes
        try:
            self.season_list.itemClicked.disconnect()
        except: pass
        self.season_list.itemClicked.connect(self.load_episodes)

    def load_image(self, url):
        if not url: return
        self.loader = ImageLoader(url)
        self.loader.signals.finished.connect(self.on_image_loaded)
        QThreadPool.globalInstance().start(self.loader)

    def on_image_loaded(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.poster_label.setPixmap(pixmap.scaled(self.poster_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def __del__(self):
        if self.loader:
            self.loader.cancel()

    def load_episodes(self, item):
        season_num = item.data(Qt.UserRole)
        episodes = self.episodes_map.get(season_num, [])
        self.episode_list.clear()
        for ep in episodes:
            name = ep.get('title', f"Episode {ep.get('episode_num', '?')}")
            list_item = QListWidgetItem(name)
            list_item.setData(Qt.UserRole, ep)
            self.episode_list.addItem(list_item)

    def on_play_clicked(self):
        # For movies
        self.play_clicked.emit(self.current_data)

    def on_episode_double_clicked(self, item):
        ep_data = item.data(Qt.UserRole)
        self.play_clicked.emit(ep_data)
