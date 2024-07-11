from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

class MyLabel(QLabel):
    def __init__(self, parent=None):
        super(MyLabel, self).__init__((parent))
        self.setGeometry(parent.geometry())
        self.setStyleSheet('background-color: rgb(48, 105, 176);')
        self.setContextMenuPolicy(Qt.CustomContextMenu)

class AdaptableLabel(QLabel):
    def __init__(self, parent=None,operation=None,pixmap=None):
        super(AdaptableLabel, self).__init__(parent)
        self.operation=operation
        self.parent = parent
        self.init_ui()
        self.setGeometry(0, 0, parent.geometry().width(), parent.geometry().height())
        self.setPixmap(pixmap)
        self.setStyleSheet('background-color: rgb(48, 105, 176);')
    def init_ui(self):
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.inner_label = MyLabel(parent = self.scroll_area)
        self.inner_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.inner_label)
        self.scroll_area.setGeometry(self.geometry())


    def setPixmap(self,pixmap):
        self.inner_label.setPixmap(pixmap)
        self.inner_label.setFixedSize(pixmap.size())
        self.inner_label.adjustSize()
        self.scroll_area.resize(pixmap.size())
        self.scroll_area.move(self.width() // 2 - pixmap.width() // 2,
                              self.height() // 2 - pixmap.height() // 2)
        self.scroll_area.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scroll_area.setGeometry(self.geometry())


