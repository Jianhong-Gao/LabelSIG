from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QDialog, QTreeWidget, QTreeWidgetItem, QWidget
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QDialog, QTreeWidget, QTreeWidgetItem, QWidget
from PyQt5.QtCore import Qt

class TreeDialog(QDialog):
    def __init__(self, parent=None):
        super(TreeDialog, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setWindowTitle("统计结果")
        self.resize(300, 400)  # 您可以根据需要调整大小
        self.layout = QVBoxLayout(self)

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setHeaderLabels(['Key', 'Value'])
        self.layout.addWidget(self.tree_widget)

        self.button_close = QPushButton("关闭", self)
        self.button_close.clicked.connect(self.close)
        self.layout.addWidget(self.button_close)

    def populate_tree(self, statistics):
        self.tree_widget.clear()  # 清除旧的项目
        self.add_items(self.tree_widget.invisibleRootItem(), statistics)

    def add_items(self, parent, elements):
        for key, value in elements.items():
            item = QTreeWidgetItem(parent)
            if isinstance(value, dict):
                item.setText(0, key)
                item.setText(1, str(value.get('total', '')))
                self.add_items(item, value)
            else:
                item.setText(0, key)
                item.setText(1, str(value))

class DemoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo Application")
        self.resize(400, 200)
        layout = QVBoxLayout(self)
        self.button_show_tree = QPushButton("显示统计数据", self)
        self.button_show_tree.clicked.connect(self.show_tree_dialog)
        layout.addWidget(self.button_show_tree)

    def show_tree_dialog(self):
        example_data = {
            "Fruits": {
                "total": 100,
                "Apple": 40,
                "Banana": 60
            },
            "Animals": {
                "total": 150,
                "Dog": 50,
                "Cat": 50,
                "Bird": 50
            }
        }
        tree_dialog = TreeDialog(self)
        tree_dialog.populate_tree(example_data)
        tree_dialog.exec_()

if __name__ == '__main__':
    app = QApplication([])
    demo = DemoApp()
    demo.show()
    app.exec_()