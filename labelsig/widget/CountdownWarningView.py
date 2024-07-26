from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class WarningDialog(QDialog):
    def __init__(self, parent=None):
        super(WarningDialog, self).__init__(parent)
        self.setWindowTitle('Warning')
        self.setFixedSize(400, 100)

        self.countdown_label = QLabel(self)
        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.close)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown_label)
        self.countdown_time = 3
        self.update_countdown_label()

        layout = QVBoxLayout(self)
        layout.addWidget(self.countdown_label)
        layout.addWidget(self.cancel_button)

        self.timer.start(1000)

    def update_countdown_label(self):
        self.countdown_time -= 1
        self.countdown_label.setText(
            f'The operation will be performed in {self.countdown_time} seconds. \nClick "Cancel" to stop.')

        if self.countdown_time == 0:
            self.timer.stop()
            self.accept()
