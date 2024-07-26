import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from labelsig.widget.MainView import MainWindow
from labelsig.utils import get_parent_directory

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    root_labelsig = get_parent_directory(levels_up=1)
    icon_path = os.path.join(root_labelsig, 'resource', 'logo.ico')
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
