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
══════════ 标签栏目详解 ══════════
[•] NE(Normal Event): 
    正常事件检测
[•] UNK(Unknown): 
    未知
[✦] PE(Pernament Event): 
    永久性事件检测
    ┌─ Fault Type:
    │  [>] HIF(High Impedance Fault): 高阻故障
    │  [>] SPG(Single Phase Ground): 单相接地故障
    │  [>] DIS(Disturbance): 扰动事件
    │
    └─ Fault Location:
       [>] FN(Fault Node): 故障节点
       [>] SN(Sound Node): 正常节点
       [>] AN(Abnormal Node): 异常节点
[✦] TE(Transient Event): 
    瞬时性事件检测
    ┌─ Fault Type:
    │  [>] HIF(High Impedance Fault): 高阻故障
    │  [>] SPG(Single Phase Ground): 单相接地故障
    │  [>] DIS(Disturbance): 扰动事件
    │
    └─ Fault Location:
       [>] FN(Fault Node): 故障节点
       [>] SN(Sound Node): 正常节点
       [>] AN(Abnormal Node): 异常节点
═══════════ 表格功能详解 ═══════════
[※] Clip Channel: 
    裁剪Comtrade文档通道
[※] Unlock: 
    解锁表格，使其可标注
[※] Confirm: 
    确认标注结果
[※] Visualize: 
    可视化零序电压和零序电流数据
    若含有多条零序电流，则无法显示
[※] Clear: 
    清除缓存
[※] Segmentation: 
    语义分割标注，可标注多个故障类型
    '''
        self.setText(content)
        self.setStandardButtons(QMessageBox.Ok)
        self.setFixedSize(400, 600)


class DemoMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(DemoMainWindow, self).__init__(parent)

        # Set up main window properties
        self.setWindowTitle("Demo App")
        self.setGeometry(400, 400, 400, 300)

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
