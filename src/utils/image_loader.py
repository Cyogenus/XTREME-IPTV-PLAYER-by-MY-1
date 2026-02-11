import requests
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, QByteArray, Qt

class ImageLoaderSignals(QObject):
    finished = pyqtSignal(QByteArray)
    error = pyqtSignal(str)

class ImageLoader(QRunnable):
    def __init__(self, url, width=170, height=220):
        super().__init__()
        self.url = url
        self.target_size = (width, height)
        self.signals = ImageLoaderSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            return
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            if not self._is_cancelled:
                # Instead of emitting raw bytes, we can emit the pixmap if needed, 
                # but QPixmap is not thread-safe. So we skip and just return raw for now.
                # HOWEVER, we can use QImage for background scaling
                from PyQt5.QtGui import QImage
                image = QImage.fromData(response.content)
                if not image.isNull():
                    scaled_image = image.scaled(self.target_size[0], self.target_size[1], 
                                               Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    # Convert back to data or just emit something safer.
                    # QImage is safer to pass between threads than QPixmap.
                    self.signals.finished.emit(QByteArray(response.content)) # Keeping simple for now
        except Exception as e:
            if not self._is_cancelled:
                self.signals.error.emit(str(e))
