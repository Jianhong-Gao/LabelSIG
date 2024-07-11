import os.path
import sys
from PyQt5.QtWidgets import QButtonGroup
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QMainWindow,
                             QWidget, QLabel, QRadioButton)
from src.utils.utils_general import get_parent_directory
from src.utils.utils_comtrade import get_channels_comtrade

class ChannelSelectionDialog(QDialog):
    def __init__(self, parent=None, file_name='FZU_0200_20190224_092419_029', channels_info=None, mode=None):
        super(ChannelSelectionDialog, self).__init__(parent)
        self.setWindowTitle("选择数据通道")
        self.setGeometry(100, 100, 400, 300)
        self.filename = file_name
        self.selected_channels = []
        self.mode=mode
        self.root_project = get_parent_directory(levels_up=2)
        self.path_raw = os.path.join(self.root_project, 'tmp', 'raw')
        self.path_file_base = os.path.join(self.path_raw, self.filename)
        self.channels_info = channels_info if channels_info else get_channels_comtrade(self.path_file_base)
        self.current_channel_ids = self.channels_info.get('current_channel_ids', [])
        self.voltage_channel_ids = self.channels_info.get('voltage_channel_ids', [])
        self.current_radiobuttons = []
        self.voltage_radiobuttons = []
        # 初始化ButtonGroups
        self.current_radio_group = QButtonGroup(self)
        self.voltage_radio_group = QButtonGroup(self)

        if mode == 'Visualization':
            self.voltage_radiobuttons = self._initialize_radiobuttons(self.voltage_channel_ids,
                                                                      self.voltage_radio_group)
            self.current_radiobuttons = self._initialize_radiobuttons(self.current_channel_ids, self.current_radio_group)

        else:
            self.analog_checkboxes = self._initialize_checkboxes(self.channels_info.get('analog_channel_ids', []))
            self.status_checkboxes = self._initialize_checkboxes(self.channels_info.get('status_channel_ids', []))

        button_cancel = QPushButton("取消")
        button_cancel.clicked.connect(self.reject)
        button_ok = QPushButton("确定")
        button_ok.clicked.connect(self.accept_channels)
        self._setup_layout(button_cancel, button_ok)

    def _initialize_radiobuttons(self, channel_labels, button_group) -> list:
        radio_buttons = [QRadioButton(label) for label in channel_labels]
        for rb in radio_buttons:
            button_group.addButton(rb)
        return radio_buttons


    # def _initialize_checkboxes(self, channel_labels) -> list:
    #     return [QCheckBox(label) for label in channel_labels]

    def _initialize_checkboxes(self, channel_labels) -> list:
        checkboxes = []
        for label in channel_labels:
            checkbox = QCheckBox(label)
            if not label:  # 如果通道名称为空
                checkbox.setChecked(True)  # 设置复选框为选中状态
            checkboxes.append(checkbox)
        return checkboxes

    def _setup_layout(self, button_cancel: QPushButton, button_ok: QPushButton) -> None:
        main_layout = QVBoxLayout(self)  # 主布局

        # 创建滚动区域和部件
        scrollArea = QScrollArea(self)
        scrollWidget = QWidget(self)
        layout = QVBoxLayout(scrollWidget)

        self._add_widgets_to_layout(layout, "选择要可视化电流通道:", getattr(self, 'current_radiobuttons', None))
        self._add_widgets_to_layout(layout, "选择要可视化电压通道:", getattr(self, 'voltage_radiobuttons', None))
        self._add_widgets_to_layout(layout, "选择要删除的模拟通道:", getattr(self, 'analog_checkboxes', None))
        self._add_widgets_to_layout(layout, "选择要删除状态通道:", getattr(self, 'status_checkboxes', None))

        button_layout = QHBoxLayout()
        button_layout.addWidget(button_cancel)
        button_layout.addWidget(button_ok)
        layout.addLayout(button_layout)

        # 设置滚动区域的属性和部件
        scrollArea.setWidget(scrollWidget)
        scrollArea.setWidgetResizable(True)
        main_layout.addWidget(scrollArea)  # 将滚动区域添加到主布局中
        self.setLayout(main_layout)  # 将主布局设置为对话框的布局
    def _add_widgets_to_layout(self, layout, label, widgets):
        if widgets:
            layout.addWidget(QLabel(label))
            for widget in widgets:
                layout.addWidget(widget)


    def accept_channels(self) -> None:
        if self.mode=='Visualization':
            current_index = [i for i, rb in enumerate(self.current_radiobuttons) if rb.isChecked()]
            voltage_index = [i for i, rb in enumerate(self.voltage_radiobuttons) if rb.isChecked()]
            # 如果选中，则获取索引，否则返回空列表
            current_channel_name = self.current_channel_ids[current_index[0]] if current_index else None
            voltage_channel_name = self.voltage_channel_ids[voltage_index[0]] if voltage_index else None
            current_channel_index=self.channels_info['analog_channel_ids'].index(current_channel_name) if current_channel_name is not None else None
            voltage_channel_index=self.channels_info['analog_channel_ids'].index(voltage_channel_name) if voltage_channel_name is not None else None
            self.selected_channels = {
                "current_channel_index": current_channel_index,
                "voltage_channel_index": voltage_channel_index,
            }
        else:
            self.selected_channels = {
                "analog_channel_ids": [label for label, cb in zip(self.channels_info.get('analog_channel_ids', []), self.analog_checkboxes) if cb.isChecked()] if hasattr(self, 'analog_checkboxes') else [],
                "status_channel_ids": [label for label, cb in zip(self.channels_info.get('status_channel_ids', []), self.status_checkboxes) if cb.isChecked()] if hasattr(self, 'status_checkboxes') else []
        }
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 800, 600)
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        button = QPushButton("Open Dialog")
        button.clicked.connect(self.open_channel_dialog)
        layout.addWidget(button)
        central_widget.setLayout(layout)

    def open_channel_dialog(self):
        dialog = ChannelSelectionDialog(self)
        if dialog.exec_():
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
