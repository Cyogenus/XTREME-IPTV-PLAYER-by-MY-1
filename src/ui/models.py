from PyQt5.QtCore import QAbstractListModel, Qt, QModelIndex

class ContentModel(QAbstractListModel):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self._items = items or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        item = self._items[index.row()]
        
        if role == Qt.UserRole:
            return item
        elif role == Qt.DisplayRole:
            return item.get('name', 'Unknown')
        
        return None

    def set_items(self, items):
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._items = []
        self.endResetModel()
