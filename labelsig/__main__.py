import sys
import os
added_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(added_path)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import logging
from labelsig.utils import get_parent_directory
path_project = get_parent_directory(levels_up=1)
path_log_dir = os.path.join(path_project, 'log')
# 检查日志目录是否存在，如果不存在则创建
if not os.path.exists(path_log_dir):
    os.makedirs(path_log_dir)
path_log = os.path.join(path_log_dir, 'LabelSIG.log')
logging.basicConfig(level=logging.DEBUG,
                    filename=f"{path_log}",
                    filemode='a',
                    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger("LabelSIG")


from labelsig.widget.MainView import MainWindow


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)

    icon_path = os.path.join(path_project, 'resource', 'logo.ico')
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()



