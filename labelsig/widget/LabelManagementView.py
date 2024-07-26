# -*-coding:utf-8-*-
import os.path
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ..utils import get_parent_directory,write_dict_to_file,read_or_create_file
from labelsig.ui_generated.ui_label_management_view import Ui_input_dialog

def generate_random_color(existing_colors):
    while True:
        color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        if not any(color.name() == v["color"] for v in existing_colors.values()):
            return color

def generate_random_value(existing_values, min_value=0, max_value=255):
    while True:
        value = random.randint(min_value, max_value)
        if not any(value == v["value"] for v in existing_values.values()):
            return value


class EditLabelDialog(QDialog):
    def __init__(self, label_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Labels")
        self.label_info = label_info

        self.initUI()
    def initUI(self):
        layout = QVBoxLayout(self)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(["Name", "Color", "Value"])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.update_table()

        layout.addWidget(self.tableWidget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def update_table(self):
        self.tableWidget.setRowCount(len(self.label_info))
        for i, info in enumerate(self.label_info):
            name_item = QTableWidgetItem(info["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 0, name_item)

            color_button = QPushButton()
            color_button.setStyleSheet(f"background-color: {info['color']}")
            color_button.clicked.connect(lambda checked, row=i: self.change_color(row))
            self.tableWidget.setCellWidget(i, 1, color_button)

            value_item = QTableWidgetItem(str(info["value"]))
            self.tableWidget.setItem(i, 2, value_item)

    def change_color(self, row):
        current_color = QColor(self.tableWidget.cellWidget(row, 1).styleSheet().split(':')[1].strip())
        color = QColorDialog.getColor(current_color, self, "Choose a color")
        if color.isValid():
            self.tableWidget.cellWidget(row, 1).setStyleSheet(f"background-color: {color.name()}")

    def get_updated_label_info(self):
        for i in range(self.tableWidget.rowCount()):
            name = self.tableWidget.item(i, 0).text()
            color = QColor(self.tableWidget.cellWidget(i, 1).styleSheet().split(':')[1].strip()).name()
            value = int(self.tableWidget.item(i, 2).text())
            self.label_info[i] = {"name": name, "color": color, "value": value}
        return self.label_info

class MyDialog(QDialog, Ui_input_dialog):
    _startPos = None
    _endPos = None
    _isTracking = False
    mySignal = pyqtSignal(str)
    def __init__(self, operation = None,class_label =['标签1', '标签2', '标签3']):
        super(MyDialog, self).__init__(operation)
        self.setupUi(self)

        self.root_labelsig=get_parent_directory(levels_up=1)
        self.path_resource=os.path.join(self.root_labelsig,'resource')
        self.operation=operation
        self.class_label=class_label
        self.setGeometry(155, 40, 349, 250)
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框
        self.initUI()
        self.set_button_image()
        self.set_qlabel_image()

    # 定义一个函数存放图片给label
    def set_button_image(self):
        self.button_close.setIcon(QIcon(os.path.join(self.path_resource,'close.png')))
        self.button_max.setIcon(QIcon(os.path.join(self.path_resource,'max.png')))
        self.button_min.setIcon(QIcon(os.path.join(self.path_resource,'min.png')))

    def set_qlabel_image(self):
        pixmap = QPixmap(os.path.join(self.path_resource,'WindowIcon.png')).scaled(self.label_logo.size(), Qt.IgnoreAspectRatio)
        self.label_logo.setPixmap(pixmap)

    def initUI(self):
        self.list_info=[]
        self.root_labelsig = self.operation.root_labelsig
        self.path_dict=self.operation.path_dict
        self.path_raw=self.operation.path_raw
        self.path_annotation=self.operation.path_annotation
        self.path_tmp=self.operation.path_tmp
        self.path_config=self.operation.path_config
        self.button_confirm.clicked.connect(self.confirm)
        self.button_cancel.clicked.connect(self.cancel)
        self.button_delete.clicked.connect(self.delete_label)
        self.listWidget.itemClicked.connect(self.update_data)
        self.button_close.clicked.connect(self.close)
        self.button_edit.clicked.connect(self.edit)
        self.update_widget()


    def edit(self):
        label_info = [{"name": k, "color": v["color"], "value": v["value"]} for k, v in self.config_annotation.items()]
        edit_dialog = EditLabelDialog(label_info, self)
        result = edit_dialog.exec_()
        if result == QDialog.Accepted:
            updated_label_info = edit_dialog.get_updated_label_info()
            updated_config = {info["name"]: {"color": info["color"], "value": info["value"]} for info in
                              updated_label_info}
            self.config_annotation = updated_config

            write_dict_to_file(dictionary=self.config_annotation, file_path=self.path_config + '/Annotation.config')
            self.update_widget()

    def send_label_name(self,label_name = None):
        self.mySignal.emit(label_name) # 发射信号

    def confirm(self):
        name_label = self.lineEdit.text().strip()  # 使用strip()去除可能的首尾空格
        if not name_label:  # 直接检查字符串是否为空
            self.lineEdit.setPlaceholderText("请选择或输入标签")
            return  # 如果没有输入，则提前退出函数
        if name_label not in self.config_annotation:
            # 获取颜色，如果用户没有选择颜色则生成一个随机颜色
            color = QColorDialog.getColor()
            hex_color = color.name() if color.isValid() else generate_random_color(self.config_annotation)
            # 生成随机值，无需检查ok1，因为已经确保会有一个有效的hex_color
            value = generate_random_value(self.config_annotation)
            # 更新配置字典并写入文件
            self.config_annotation[name_label] = {'color': hex_color, 'value': value}
            write_dict_to_file(dictionary=self.config_annotation,
                               file_path=os.path.join(self.path_config, 'Annotation.config'))
            self.update_widget()  # 更新界面
        # 发送标签名并关闭对话框
        self.label = name_label
        self.send_label_name(self.label)
        self.close()

    def cancel(self):
        self.send_label_name()
        self.close()
    def update_data(self):
        self.lineEdit.setText(self.listWidget.currentItem().text())
    def delete_label(self):
        label_name = self.listWidget.currentItem().text()
        if label_name!='':
            del self.config_annotation[label_name]
            write_dict_to_file(dictionary=self.config_annotation, file_path=self.path_config + '/Annotation.config')
            self.update_widget()
        else:
            self.lineEdit.setPlaceholderText("未选中需要删除的标签")
    def update_widget(self):
        self.config_annotation = read_or_create_file(self.path_config, "Annotation.config")
        category_name=list(self.config_annotation.keys())
        self.listWidget.clear()
        self.listWidget.addItems(category_name)
    def mouseMoveEvent(self, e: QMouseEvent):  # 重写移动事件
        self._endPos = e.pos() - self._startPos
        self.move(self.pos() + self._endPos)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._isTracking = True
            self._startPos = QPoint(e.x(), e.y())

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._isTracking = False
            self._startPos = None
            self._endPos = None

