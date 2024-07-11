import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from src.widget.MainView import MainWindow
from src.utils.utils_general import get_parent_directory
if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    root_project=get_parent_directory(levels_up=2)
    icon_path = os.path.join(root_project, 'resource', 'logo.ico')
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    MainWindow = MainWindow()
    MainWindow.show()
    sys.exit(app.exec_())
    # pyinstaller --onefile --noconsole --name CabrSIG main.py