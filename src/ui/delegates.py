from PyQt5.QtWidgets import QStyledItemDelegate, QStyle
from PyQt5.QtCore import Qt, QRect, QSize, QThreadPool, QByteArray, QTimer
from PyQt5.QtGui import QPixmap, QColor, QFont, QImage
from src.utils.image_loader import ImageLoader

# Dedicated pool for images to allow mass cancellation
IMAGE_POOL = QThreadPool()
IMAGE_POOL.setMaxThreadCount(4)

class ImageCache:
    _cache = {}
    _max_items = 150 # Reduced to keep memory very lean

    @classmethod
    def get(cls, url):
        return cls._cache.get(url)

    @classmethod
    def set(cls, url, pixmap):
        if len(cls._cache) >= cls._max_items:
            # Clear all if limit hit - safer than popping one by one for memory fragmentation
            cls._cache.clear()
        cls._cache[url] = pixmap

    @classmethod
    def clear(cls):
        cls._cache.clear()

class ContentDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.poster_width = 170
        self.poster_height = 220
        self.padding = 10
        self.item_width = 180
        self.item_height = 280
        
        # Debouncing
        self.load_queue = {} # url -> timer
        self._loading_urls = set()

    def paint(self, painter, option, index):
        data = index.data(Qt.UserRole)
        if not data:
            return

        painter.save()
        painter.setRenderHint(painter.Antialiasing)

        # Background
        rect = option.rect
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, QColor(59, 130, 246, 50))
            painter.setPen(QColor(59, 130, 246))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        
        # Poster Area
        poster_rect = QRect(rect.left() + 5, rect.top() + 5, self.poster_width, self.poster_height)
        
        img_url = (data.get('stream_icon') or data.get('movie_image') or 
                   data.get('movie_icon') or data.get('cover') or 
                   data.get('series_cover') or data.get('icon') or data.get('poster'))

        pixmap = ImageCache.get(img_url)
        if pixmap:
            painter.drawPixmap(poster_rect, pixmap)
        else:
            # Placeholder and start loader
            painter.fillRect(poster_rect, QColor(30, 41, 59))
            if img_url:
                self.trigger_image_load(img_url, index)

        # Title
        title = data.get('name', 'Unknown')
        title_rect = QRect(rect.left() + 5, rect.top() + self.poster_height + 10, self.poster_width, 30)
        painter.setPen(Qt.white)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.TextWordWrap, title)

        # Rating
        rating = data.get('rating') or data.get('rating_5based', 'N/A')
        rating_rect = QRect(rect.left() + 5, rect.top() + self.poster_height + 40, self.poster_width, 20)
        painter.setPen(QColor("#fbbf24"))
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(rating_rect, Qt.AlignLeft, f"⭐ {rating}")

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(self.item_width, self.item_height)

    def trigger_image_load(self, url, index):
        if url in self._loading_urls or url in self.load_queue:
            return

        # Start a debounce timer (250ms)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda u=url, i=index: self.start_actual_load(u, i))
        self.load_queue[url] = timer
        timer.start(250)

    def start_actual_load(self, url, index):
        if url in self.load_queue:
            self.load_queue.pop(url)
            
        if url in self._loading_urls:
            return
            
        self._loading_urls.add(url)
        loader = ImageLoader(url, self.poster_width, self.poster_height)
        loader.signals.finished.connect(lambda data: self.on_image_loaded(url, data, index))
        IMAGE_POOL.start(loader)

    def on_image_loaded(self, url, data, index):
        if url in self._loading_urls:
            self._loading_urls.remove(url)
            
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            scaled_pixmap = pixmap.scaled(self.poster_width, self.poster_height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            ImageCache.set(url, scaled_pixmap)
            # Notify the view to repaint this index
            if hasattr(self.parent(), 'viewport'):
                self.parent().viewport().update()
