import sys
from qtpy.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QMessageBox
# from PyQt5.QtGui import QPalette, QColor

class HelpDialog(QMessageBox):
    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        # Set palette for black background and white text
        self.setStyleSheet("""
        QMessageBox {
            background-color: black;
        }
        QLabel {
            color: white;
        }
        QAbstractButton {
            color: black;
        }
        """)
        self.setIcon(QMessageBox.Information)
        self.setWindowTitle("帮助")

        content = '''
═══════════ 软件功能详解 ═══════════
[※] Fault Detection: 
    语义分割标注，实现采样点级别的单标签分类
[※] Fault Identification: 
    语义分割标注，实现采样点级别的多标签分类
[※] Fault Localization: 
    故障选段或区段定位标注：
    【故障馈线、健全馈线、模糊馈线、参考信号】  
═══════════ 表格功能详解 ═══════════
[※] Clip Channel: 
    裁剪Comtrade文档通道
[※] Unlock: 
    解锁表格，使其可标注
[※] Confirm: 
    确认Comtrade文件Trigger Index的校正结果
[※] Clear: 
    清除缓存
    '''
        self.setText(content)
        self.setStandardButtons(QMessageBox.Ok)
        self.setFixedSize(400, 400)


class DemoMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(DemoMainWindow, self).__init__(parent)

        # Set up main window properties
        self.setWindowTitle("Demo App")
        self.setGeometry(400, 400, 400, 200)

        # Create Help Button
        self.helpButton = QPushButton("显示帮助", self)
        self.helpButton.clicked.connect(self.show_help)

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(self.helpButton)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = DemoMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
