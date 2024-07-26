import sys
import os
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QIcon
from qtpy.QtCore import Qt
from labelsig.widget.MainView import MainWindow
from labelsig.utils import get_parent_directory
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
    # pyinstaller --onefile --noconsole --name CabrSIG __main__.py