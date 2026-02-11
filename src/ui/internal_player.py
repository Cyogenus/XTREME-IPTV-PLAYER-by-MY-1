import vlc
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton, QSlider, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from src.api.xtream_api import CUSTOM_USER_AGENT

class InternalPlayer(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instance = vlc.Instance(f"--http-user-agent={CUSTOM_USER_AGENT}")
        self.player = self.instance.media_player_new()
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_ui)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Video Container
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.layout.addWidget(self.video_frame)
        
        # Controls
        self.controls = QFrame()
        self.controls.setFixedHeight(80)
        self.controls.setStyleSheet("background-color: rgba(15, 23, 42, 0.9);")
        controls_layout = QVBoxLayout(self.controls)
        
        # Seek bar
        self.seek_bar = QSlider(Qt.Horizontal)
        self.seek_bar.setRange(0, 1000)
        self.seek_bar.sliderMoved.connect(self.set_position)
        controls_layout.addWidget(self.seek_bar)
        
        # Buttons
        btns_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("← EXIT")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self.back_clicked.emit) # Only emit, MainWindow will call stop
        btns_layout.addWidget(self.back_btn)
        
        btns_layout.addStretch()
        
        self.play_pause_btn = QPushButton("⏸")
        self.play_pause_btn.setFixedSize(40, 40)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        btns_layout.addWidget(self.play_pause_btn)
        
        btns_layout.addStretch()
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white;")
        btns_layout.addWidget(self.time_label)
        
        controls_layout.addLayout(btns_layout)
        self.layout.addWidget(self.controls)
        
        # Platform specific video output
        import sys
        if sys.platform.startswith('linux'):
            self.player.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform == 'win32':
            self.player.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform == 'darwin':
            self.player.set_nsobject(int(self.video_frame.winId()))

    def play(self, url):
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self.play_pause_btn.setText("⏸")
        self.timer.start()

    def stop(self):
        self.timer.stop()
        
        # Move VLC stop to background thread to prevent UI freeze
        # This is CRITICAL if the network stream is slow to close
        import threading
        def _async_stop():
            try:
                self.player.stop()
                self.player.set_media(None)
            except:
                pass
        
        thread = threading.Thread(target=_async_stop)
        thread.daemon = True
        thread.start()

        self.play_pause_btn.setText("▶")

    def toggle_play_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_btn.setText("▶")
        else:
            self.player.play()
            self.play_pause_btn.setText("⏸")

    def set_position(self, value):
        self.player.set_position(value / 1000.0)

    def update_ui(self):
        if not self.player.is_playing() and self.player.get_state() != vlc.State.Paused:
            return
            
        pos = int(self.player.get_position() * 1000)
        self.seek_bar.setValue(pos)
        
        m_time = self.player.get_time() // 1000
        total_time = self.player.get_length() // 1000
        
        if total_time > 0:
            self.time_label.setText(f"{self.format_time(m_time)} / {self.format_time(total_time)}")
        else:
            self.time_label.setText(f"{self.format_time(m_time)} / Live")

    def format_time(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02}:{m:02}:{s:02}"
        return f"{m:02}:{s:02}"
