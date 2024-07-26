import sys
import os
import stat

import shutil
from datetime import datetime
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QFont,QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QTreeWidgetItem,
    QTableWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QCheckBox,
    QRadioButton,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QToolTip,
    QMessageBox,
)
from labelsig.ui_generated.ui_main_view import Ui_MainWindow
from labelsig.widget.StatisticsTreeView import TreeDialog
from labelsig.widget.WaveformVisualizerView import WaveformVisualizerDialog
from labelsig.widget.ChannelSelectionView import ChannelSelectionDialog
from labelsig.widget.SegmentationView import SegmentationPage
from labelsig.widget.LocationView import LocationPage
from labelsig.widget.HelpView import HelpDialog
from labelsig.utils import get_parent_directory
from labelsig.utils import single_visualize
from labelsig.utils import load_annotation
from labelsig.utils import get_annotation_info, update_annotation_label
from labelsig.utils import update_comtrade, delete_specific_channels

style_enable = "color: rgb(255, 255, 255);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(48, 105, 176);border-radius: 16px;"
style_disable = "color: rgb(0, 0, 0);\nfont: 25pt 'Bahnschrift Condensed';\nbackground-color: rgb(169, 169, 197);border-radius: 16px;"


class BatchVisualizeThread(QThread):
    completed = pyqtSignal()  # 用于发送线程完成信号
    def __init__(self, filenames, path_output, path_source, mainwindow=None):
        super(BatchVisualizeThread, self).__init__()
        self.filenames = filenames
        self.path_output = path_output
        self.path_source = path_source
        self.mainwindow = mainwindow
        self.label_info = mainwindow.label_info
        self.path_annotation = mainwindow.path_annotation

    def run(self):
        total_files = len(self.filenames)
        bar_length = 50  # 你可以根据需要设置进度条长度
        for i, filename in enumerate(self.filenames):
            progress_ratio = (i + 1) / total_files
            filled_length = int(bar_length * progress_ratio)
            # 创建进度条字符串
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            flag = str(i + 1) + '/' + str(total_files)
            # 更新label_info来显示进度条、文件计数以及文件名
            self.label_info.setText(f"[{bar}] {flag} 正在绘制: {filename}")
            path_file_ann = os.path.join(self.path_annotation, filename + '.ann')
            annotation = load_annotation(path_file_ann)
            single_visualize(filename, self.path_output, self.path_source, annotation)
        self.label_info.setText("[{}] 所有文件处理完毕！".format('█' * bar_length))


class LoadFolderThread(QThread):
    signal_finished = pyqtSignal(str, dict)
    signal_duplicate_files = pyqtSignal(list)  # Signal to inform the main thread about duplicate files.

    def __init__(self, mainwindow, path_dict, path_source):
        super().__init__()
        self.main_window = mainwindow
        self.root_labelsig = get_parent_directory(levels_up=1)
        self.path_tmp = os.path.join(self.root_labelsig, 'tmp')
        self.path_raw = os.path.join(self.path_tmp, 'raw')
        self.path_annotation = os.path.join(self.path_tmp, 'annotation')
        self.path_source = path_source
        self.path_dict = path_dict

    def run(self):
        source_raw = os.path.join(self.path_source, 'raw')
        source_annotation = os.path.join(self.path_source, 'annotation')
        if os.path.exists(source_raw) and os.path.exists(source_annotation):
            duplicate_files = self.import_from_folders(source_raw, self.path_raw) + \
                              self.import_from_folders(source_annotation, self.path_annotation)
            if duplicate_files:
                self.signal_duplicate_files.emit(duplicate_files)
        else:
            self.import_other_files()
        dict_info = get_dict(self.path_dict, qlabel=self.main_window.label_info)
        self.signal_finished.emit(self.path_source, dict_info)

    def import_from_folders(self, source_folder, target_folder):
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        # List of duplicate files
        duplicates = []
        # List all files in the source folder and copy to target folder
        for file_name in os.listdir(source_folder):
            file_path = os.path.join(source_folder, file_name)
            target_path = os.path.join(target_folder, file_name)
            # Check if the file already exists in the target folder
            if os.path.exists(target_path):
                duplicates.append(file_name)
            else:
                shutil.copy(file_path, target_folder)
        return duplicates

    def import_other_files(self):
        if not os.path.exists(self.path_raw):
            os.makedirs(self.path_raw)
        # 获取目标目录中所有已存在的文件的基本名（不带扩展名）
        existing_files = {os.path.splitext(f)[0] for f in os.listdir(self.path_raw)
                          if os.path.isfile(os.path.join(self.path_raw, f))}
        list_files = os.listdir(self.path_source)

        total_files = len(list_files)
        bar_length = 50  # 你可以根据需要设置进度条长度

        for i, file_name in enumerate(list_files):
            progress_ratio = (i + 1) / total_files
            filled_length = int(bar_length * progress_ratio)

            # 创建进度条字符串
            bar = '█' * filled_length + '-' * (bar_length - filled_length)

            flag = str(i + 1) + '/' + str(total_files)
            # 更新label_info来显示进度条、文件计数以及文件名
            self.main_window.label_info.setText(f"[{bar}] {flag} 正在导入: {file_name}")

            file_path = os.path.join(self.path_source, file_name)
            if os.path.isfile(file_path):
                base_name = os.path.splitext(file_name)[0]
                if base_name not in existing_files:
                    shutil.copy(file_path, self.path_raw)

        # 所有文件都被导入后，更新label_info的信息
        self.main_window.label_info.setText("[{}] 所有文件导入完毕！".format('█' * bar_length))


import time


def get_dict(path_dict, qlabel=None, bar_length=50):
    if qlabel is not None:
        # 设置等宽字体
        font = QFont("Courier New")
        font.setPointSize(12)  # 根据需要设置字体大小
        qlabel.setFont(font)

    path_raw = path_dict['path_raw']
    path_annotation = path_dict['path_annotation']
    unique_base_files = {os.path.splitext(f)[0] for f in os.listdir(path_raw) if
                         os.path.isfile(os.path.join(path_raw, f))}
    sorted_base_files = sorted(unique_base_files)
    dict_info = {}
    total_files = len(sorted_base_files)
    processing_times = []  # 记录每个文件的处理时间
    for idx, file_name in enumerate(sorted_base_files):
        file_start_time = time.time()
        path_raw_base = os.path.join(path_raw, file_name)
        path_annotation_base = os.path.join(path_annotation, file_name)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        annotation = get_annotation_info(path_base_dict)
        dict_info[file_name] = annotation
        file_end_time = time.time()
        processing_times.append(file_end_time - file_start_time)
        if qlabel is not None:
            max_time_per_file = max(processing_times)
            # 这里我们考虑最大处理时间来预估剩余时间
            estimated_remaining_time = max_time_per_file * (total_files - idx - 1)
            progress_ratio = (idx + 1) / total_files
            filled_length = int(bar_length * progress_ratio)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            mins, secs = divmod(estimated_remaining_time, 60)
            qlabel.setText(
                f"[{bar}] ({idx + 1}/{total_files}) \n正在处理文件: {file_name} \n预计剩余等待时间: {int(mins)}分{int(secs)}秒")
    if qlabel is not None:
        qlabel.setText("[{}] 所有文件处理完毕！".format('█' * bar_length))
        if total_files == 0:
            qlabel.setText("[{}] 未找到任何文件！".format('█' * bar_length))
    return dict_info


class FileOpenThread(QThread):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        root_labelsig = get_parent_directory(levels_up=1)
        exe_path = os.path.join(root_labelsig, 'CAAP2008X', 'CAAP2008X.exe')  # 构建CAAP2008X.exe的绝对路径
        cfg_file_path = os.path.join(root_labelsig, self.file_path + '.cfg')  # 构建配置文件的绝对路径
        command = f'start "{exe_path}" "{cfg_file_path}"'
        os.system(command)


class StatusWidget(QWidget):
    statusChanged = pyqtSignal(str)  # 增加此信号

    def __init__(self, status_labels=None, parent=None):
        super(StatusWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.radio_buttons = {}
        for label in status_labels:
            rb = QRadioButton(label, self)
            rb.toggled.connect(self._emit_status_changed)
            self.layout.addWidget(rb)
            self.radio_buttons[label] = rb

    def _emit_status_changed(self, checked):
        if checked:
            sender = self.sender()
            self.statusChanged.emit(sender.text())

    def set_status(self, status):
        if status in self.radio_buttons:
            self.radio_buttons[status].setChecked(True)
        else:
            self.clear_status()

    def clear_status(self):
        for rb in self.radio_buttons.values():
            rb.setChecked(False)

    def current_status(self):
        """Retrieve the currently selected status."""
        for label, rb in self.radio_buttons.items():
            if rb.isChecked():
                return label
        return None


class GetDictThread(QThread):
    signal_finished = pyqtSignal(dict, str)

    def __init__(self, path_dict, qlabel=None, message=""):
        super().__init__()
        self.path_dict = path_dict
        self.message = message
        self.qlabel = qlabel

    def run(self):
        dict_info = get_dict(self.path_dict, qlabel=self.qlabel)
        self.signal_finished.emit(dict_info, self.message)


class Categories_staticatics_Thread(QThread):
    signal_finished = pyqtSignal(dict)

    def __init__(self, path_dict):
        super().__init__()
        self.path_dict = path_dict
        self.running = True

    def run(self):
        dict_info = get_dict(self.path_dict)
        statistics_tree = {
            'NE': {'total': 0},
            'PE': {
                'total': 0,
                'location': {'FN': 0, 'SN': 0, 'AN': 0, 'UNK': 0},
                'type': {'HIF': 0, 'SPG': 0, 'DIS': 0, 'UNK': 0}
            },
            'TE': {
                'total': 0,
                'location': {'FN': 0, 'SN': 0, 'AN': 0, 'UNK': 0},
                'type': {'HIF': 0, 'SPG': 0, 'DIS': 0, 'UNK': 0}
            },
            'UNK': {'total': 0}
        }
        for row, (file_name, annotation) in enumerate(dict_info.items()):
            label_detection = annotation['detection_label']
            label_location = annotation['location_label']
            label_type = annotation['type_label']
            if label_detection is None or label_detection == 'UNK':
                statistics_tree['UNK']['total'] += 1
                continue
            statistics_tree[label_detection]['total'] += 1
            if label_detection in ['PE', 'TE']:
                if label_location in statistics_tree[label_detection]['location']:
                    statistics_tree[label_detection]['location'][label_location] += 1
                if label_type in statistics_tree[label_detection]['type']:
                    statistics_tree[label_detection]['type'][label_type] += 1
        self.signal_finished.emit(statistics_tree)


class CustomTableWidget(QTableWidget):
    HEADERS = ['Filename', 'Fault Trigger', 'Event Detection', 'Event Type', 'Fault Location', 'Functions']

    def __init__(self, main_window, parent=None):
        super(CustomTableWidget, self).__init__(parent)
        self.main_window = main_window

    # ----- UI Initialization Helpers -----
    def _initialize_status_widget(self, label, status_labels=None):
        status_widget = StatusWidget(status_labels=status_labels, parent=self)
        status_widget.setEnabled(False)
        status_widget.set_status(label)
        return status_widget

    def _create_filename_cell(self, file_name):
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        checkbox = QCheckBox(self)
        layout.addWidget(checkbox)
        label = QLabel(file_name, self)
        layout.addWidget(label)
        layout.addStretch(1)  # 添加弹性空间
        button_open_file = QPushButton('Open', self)
        button_open_file.clicked.connect(self.open_file)
        layout.addWidget(button_open_file)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        return widget

    def _add_line_edit(self, row, annotation):
        line_edit = QLineEdit(self)
        line_edit.setValidator(QIntValidator(1, 99999))
        line_edit.setText(str(int(annotation['fault_trigger']) + 1))
        line_edit.setEnabled(False)
        line_edit.setAlignment(Qt.AlignCenter)
        line_edit.textChanged.connect(self._validate_line_edit)
        self.setCellWidget(row, 1, line_edit)  # Set the QLineEdit in the column

    def _validate_line_edit(self, text):
        if not text or int(text) < 1:
            sender = self.sender()  # Get the QLineEdit that emitted the signal
            sender.setText("1")

    def _add_buttons_to_function_column(self, row):
        # 创建一个容器QWidget和布局
        container_widget = QWidget(self)
        layout = QHBoxLayout(container_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建通道裁剪功能按钮
        button_clip = QPushButton('Clip Channel', self)
        button_clip.clicked.connect(self.clip_channel)
        layout.addWidget(button_clip)

        # 创建解锁按钮
        button_unlock = QPushButton('Unlock', self)
        button_unlock.clicked.connect(self.unlock_row)
        layout.addWidget(button_unlock)

        # 创建确认按钮
        button_confirm = QPushButton('Confirm', self)
        button_confirm.clicked.connect(self.confirm_edit)
        layout.addWidget(button_confirm)

        # 创建可视化按钮
        button_visualize = QPushButton('Visualize', self)
        button_visualize.clicked.connect(self.visualize_data)
        layout.addWidget(button_visualize)

        container_widget.setLayout(layout)

        self.setCellWidget(row, 5, container_widget)  # 假设第5列是"Function"列

    # ----- Core Functionalities -----

    def populate_table_from_dict(self, dict_info):
        self.clearContents()
        self.setRowCount(len(dict_info))
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.resizeColumnsToContents()

        status_definitions = [
            ("detection_status", ["NE", "PE", "TE", "UNK"]),
            ("type_status", ["HIF", "SPG", "DIS", "UNK"]),
            ("location_status", ["FN", "SN", "AN", "UNK"])
        ]
        for row, (file_name, annotation) in enumerate(dict_info.items()):
            self._populate_row_with_data(row, file_name, annotation, status_definitions)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def visualize_data(self, row=None):
        row = self._get_sender_row()
        widget = self.cellWidget(row, 0)  # 获取第 0 列的组件
        label = widget.findChild(QLabel)  # 从组件中查找 QLabel
        file_name = label.text()  # 从 QLabel 中获取文件名
        # 使用工具函数创建Matplotlib图形和Canvas
        self.matplotlib_dialog = WaveformVisualizerDialog(self.main_window, file_name)

    def clip_channel(self):
        row = self._get_sender_row()
        widget = self.cellWidget(row, 0)  # 获取第 0 列的组件
        label = widget.findChild(QLabel)  # 从组件中查找QLabel
        file_name = label.text()  # 从QLabel中获取文件名
        dialog = ChannelSelectionDialog(self, file_name=file_name, mode='Clip')
        if dialog.exec_():
            channels_info = dialog.selected_channels
            print('channels_info:',channels_info)
            analog_channel_ids = channels_info['analog_channel_ids']
            status_channel_ids = channels_info['status_channel_ids']
            print('analog_channel_ids:', analog_channel_ids)
            print('status_channel_ids:', status_channel_ids)
            delete_specific_channels(path_raw=self.main_window.path_raw, orig_name=file_name,
                                     analog_channel_ids=analog_channel_ids, status_channel_ids=status_channel_ids)

    def delete_row(self, row):
        if row is None:
            return
        widget = self.cellWidget(row, 0)  # 获取第 0 列的组件
        if widget is None:
            print(f"第 {row} 行的组件为空。")
            return
        label = widget.findChild(QLabel)  # 从组件中查找QLabel
        if label is None:
            print(f"无法在第 {row} 行的组件中找到标签。")
            return
        file_name = label.text()  # 从QLabel中获取文件名
        for ext in ['.cfg', '.dat']:
            file_path = os.path.join(self.parent().path_raw, file_name + ext)
            self._delete_file(file_path)
        for ext in ['.ann']:
            file_path = os.path.join(self.parent().path_annotation, file_name + ext)
            self._delete_file(file_path)

        self.removeRow(row)
        self.main_window.label_info.setText(f'文件 {file_name} 及其标注文件已被删除')

    def open_file(self):
        button = self.sender()  # 获取点击的按钮
        container_widget = button.parent()  # 获取按钮所在的容器控件
        label = container_widget.findChild(QLabel)  # 在容器控件中查找QLabel
        file_name = label.text()  # 从QLabel中获取文件名
        file_path = os.path.join(self.parent().path_raw, file_name)
        self.file_open_thread = FileOpenThread(file_path)
        self.file_open_thread.start()
        row = self._get_sender_row()
        if row is not None:  # 如果能获取到行号
            self._set_row_widget_enabled(row, True)
            self.main_window.label_info.setText(f'文件 {file_name} 已打开')

    def unlock_row(self):
        row = self._get_sender_row()
        if row is not None:
            self._set_row_widget_enabled(row, True)

    def confirm_edit(self):
        row = self._get_sender_row()
        fault_trigger = self.cellWidget(row, 1).text()
        fault_trigger = str(int(fault_trigger) - 1)
        detection_status = self._get_selected_status(row, 2)
        if detection_status == "NE" or detection_status == "UNK":
            type_status = "UNK"
            location_status = "UNK"

        elif detection_status is None:
            self._show_warning("请选择Fault Detection")
            return
        else:
            type_status = self._get_selected_status(row, 3)
            location_status = self._get_selected_status(row, 4)
            if None in [type_status]:
                self._show_warning("请选择Fault Type")
                return
            if None in [location_status]:  # 如果任何一个状态是None
                self._show_warning("请选择Fault Location")
                return
        self._set_row_widget_enabled(row, False)
        annotation_dict = {
            'fault_trigger': fault_trigger,
            'detection_label': detection_status,
            'type_label': type_status,
            'location_label': location_status
        }
        widget = self.cellWidget(row, 0)  # 获取第 0 列的组件
        label = widget.findChild(QLabel)  # 从组件中查找QLabel
        orig_name = label.text()  # 从QLabel中获取文件名
        path_raw_base = os.path.join(self.main_window.path_dict['path_raw'], orig_name)
        path_annotation_base = os.path.join(self.main_window.path_dict['path_annotation'], orig_name)
        path_base_dict = {'path_raw_base': path_raw_base, 'path_annotation_base': path_annotation_base}
        flag_save_annotation = update_annotation_label(path_base_dict=path_base_dict, annotation_dict=annotation_dict)
        if flag_save_annotation:
            self.main_window.label_info.setText(f'annotation文件 {orig_name}.ann 已保存')
        update_comtrade(fault_trigger=int(fault_trigger),
                        path_raw=self.main_window.path_raw, orig_name=orig_name)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def _show_warning(self, message):
        """显示警告对话框"""
        warning_message = QMessageBox(self)
        warning_message.setIcon(QMessageBox.Warning)
        warning_message.setText(message)
        warning_message.setWindowTitle("警告")
        warning_message.setStandardButtons(QMessageBox.Ok)
        warning_message.exec_()

    def get_checked_files_with_rows(self):
        checked_files_with_rows = []
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 0)
            if widget and isinstance(widget, QWidget):
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    label = widget.findChild(QLabel)
                    if label:
                        filename = label.text()
                        checked_files_with_rows.append((filename, row))

        return checked_files_with_rows

    def is_filename_checked(self, row):
        """检查给定行的文件名列的复选框是否被选中。"""
        widget = self.cellWidget(row, 0)  # 假设第0列是文件名列
        checkbox = widget.findChild(QCheckBox)  # 从小部件中获取复选框
        return checkbox.isChecked()

    # ----- Utility Functions -----
    def _populate_row_with_data(self, row, file_name, annotation, status_definitions):
        filename_cell = self._create_filename_cell(file_name)
        self.setCellWidget(row, 0, filename_cell)
        self._add_line_edit(row, annotation)
        for idx, (status_key, status_values) in enumerate(status_definitions, 2):
            status_widget = self._initialize_status_widget(annotation[status_key[:-7] + "_label"], status_values)
            self.setCellWidget(row, idx, status_widget)
            if status_key == "detection_status":
                status_widget.statusChanged.connect(self._handle_detection_status_change)
        self._add_buttons_to_function_column(row)

    def _handle_detection_status_change(self, status):
        sender_widget = self.sender()
        row = self.indexAt(sender_widget.pos()).row()
        if status == "NE" or status == "UNK":
            self.cellWidget(row, 3).set_status("UNK")
            self.cellWidget(row, 4).set_status("UNK")
            self.cellWidget(row, 3).setEnabled(False)
            self.cellWidget(row, 4).setEnabled(False)

        else:
            self.cellWidget(row, 3).setEnabled(True)
            self.cellWidget(row, 4).setEnabled(True)

    def _get_sender_row(self):
        sender_widget = self.sender()
        if sender_widget:
            global_pos = sender_widget.mapToGlobal(QPoint(0, 0))
            table_pos = self.mapFromGlobal(global_pos)
            return self.indexAt(table_pos).row()
        return None

    def _set_row_widget_enabled(self, row, enabled=True):
        for col in [1, 2, 3, 4]:
            self.cellWidget(row, col).setEnabled(enabled)

    def _get_selected_status(self, row, column):
        status_widget = self.cellWidget(row, column)
        if status_widget:
            return status_widget.current_status()
        return None

    def _delete_file(self, file_path):
        try:
            if not os.access(file_path, os.W_OK):
                # 将文件设置为可写
                os.chmod(file_path, stat.S_IWRITE)
            os.remove(file_path)
        except PermissionError:
            print(f"Permission denied: {file_path}")
            # 在此处添加任何额外的错误处理或日志记录

class ClearCacheThread(QThread):
    signal_finished = pyqtSignal()
    def __init__(self, path_dict):
        super().__init__()
        self.path_dict = path_dict

    def run(self):
        path_tmp = self.path_dict['path_tmp']
        path_raw = self.path_dict['path_raw']
        path_annotation = self.path_dict['path_annotation']
        shutil.rmtree(path_tmp)
        os.makedirs(path_raw, exist_ok=True)
        os.makedirs(path_annotation, exist_ok=True)
        self.signal_finished.emit()

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.version = '3.0.0'
        self.init_ui_elements()
        self.connect_signals()

    def init_ui_elements(self):
        self.reconfigure_table_files()
        self.setWindowTitle("LabelSIG")
        self.statusBar().showMessage(f"Version: {self.version}")
        self.root_labelsig=get_parent_directory(levels_up=1)
        self.path_dict = self.get_temp_path()
        self.path_tmp = self.path_dict['path_tmp']
        self.path_raw = self.path_dict['path_raw']
        self.path_annotation = self.path_dict['path_annotation']
        self.setup_label_info()
        layout = QVBoxLayout()
        layout.addWidget(self.label_info)
        self.setLayout(layout)
        self.init_table(message='已完成初始化')
        path_icon = self.construct_path(self.root_labelsig, 'resource', 'WindowIcon.png')
        self.setWindowIcon(QIcon(path_icon))

    def init_table(self, message=None):
        self.disable_buttons()
        self.get_dict_thread = GetDictThread(self.path_dict, qlabel=self.label_info, message=message)
        self.get_dict_thread.signal_finished.connect(self.slot_init_table)
        self.get_dict_thread.start()

    def construct_path(self, *args):
        return os.path.join(*args)

    def slot_init_table(self, dict_info, message=None):
        self.display_files_in_table(dict_info)
        if message is not None:
            self.label_info.setText(message)
        self.enable_buttons()

    def set_button_style(self, button, enable=True):
        if enable:
            button.setStyleSheet(style_enable)
        else:
            button.setStyleSheet(style_disable)
        button.setDisabled(not enable)

    def disable_buttons(self):
        self.set_button_style(self.button_load_folder, enable=False)
        self.set_button_style(self.button_output, enable=False)
        self.set_button_style(self.button_refresh, enable=False)
        self.set_button_style(self.button_delete, enable=False)
        self.set_button_style(self.button_visualize, enable=False)
        self.set_button_style(self.button_help, enable=False)
        self.set_button_style(self.button_clear_cache, enable=False)
        self.set_button_style(self.button_segmentation, enable=False)
        self.set_button_style(self.button_location, enable=False)


    def enable_buttons(self):
        self.set_button_style(self.button_load_folder, enable=True)
        self.set_button_style(self.button_output, enable=True)
        self.set_button_style(self.button_refresh, enable=True)
        self.set_button_style(self.button_delete, enable=True)
        self.set_button_style(self.button_visualize, enable=True)
        self.set_button_style(self.button_help, enable=True)
        self.set_button_style(self.button_clear_cache, enable=True)
        self.set_button_style(self.button_segmentation, enable=True)
        self.set_button_style(self.button_location, enable=True)

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

    def upgrade_staticatics(self):
        self.button_refresh.setEnabled(False)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.label_info.setText(timestamp + '--开始统计样本数量及类型.....')
        self.upgrade_staticatics_thread = Categories_staticatics_Thread(self.path_dict)
        self.upgrade_staticatics_thread.signal_finished.connect(self.slot_upgrade_staticatics)
        self.upgrade_staticatics_thread.start()

    def slot_upgrade_staticatics(self, condition_staticstics):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp as a string
        self.label_info.setText(timestamp + '--已刷新样本类型数量')
        self.button_refresh.setEnabled(True)
        tree_dialog = TreeDialog(self)
        tree_dialog.populate_tree(condition_staticstics)
        tree_dialog.exec_()  # Modal execution

    def setup_label_info(self):
        self.label_info.setWordWrap(True)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_info.setSizePolicy(size_policy)

    def get_temp_path(self):
        root_labelsig = get_parent_directory(levels_up=1)
        path_tmp = os.path.join(root_labelsig, 'tmp')
        path_tmp_raw = os.path.join(root_labelsig, 'tmp', 'raw')
        path_tmp_annotation = os.path.join(root_labelsig, 'tmp', 'annotation')
        os.makedirs(path_tmp_raw, exist_ok=True)
        os.makedirs(path_tmp_annotation, exist_ok=True)
        path_dict = {'path_raw': path_tmp_raw, 'path_annotation': path_tmp_annotation, 'path_tmp': path_tmp}
        return path_dict

    def connect_signals(self):
        QToolTip.setFont(QFont('SansSerif', 10))
        # 设置 QToolTip 的样式
        self.button_load_folder.clicked.connect(self.load_folder)
        self.button_load_folder.setToolTip('Load a folder containing raw data files')
        self.button_output.clicked.connect(self.output_files)
        self.button_output.setToolTip('Output raw data files and corresponding annotation files')
        self.button_refresh.clicked.connect(self.upgrade_staticatics)
        self.button_refresh.setToolTip('Refresh the statistics of the number of samples and types')
        self.button_delete.clicked.connect(self.delete_checked_files)
        self.button_delete.setToolTip('Delete selected files and corresponding annotation files')
        self.button_visualize.clicked.connect(self.batch_visualize_data)
        self.button_visualize.setToolTip('Batch visualize selected files')
        self.button_help.clicked.connect(self.show_help)
        self.button_help.setToolTip('Show help')
        self.button_segmentation.clicked.connect(self.segmentation_data)
        self.button_segmentation.setToolTip('Segmentation data')
        self.button_location.clicked.connect(self.location_data)
        self.button_location.setToolTip('Location data')
        self.button_clear_cache.clicked.connect(self.clear_cache)
        self.button_clear_cache.setToolTip('Clear cache')

    def location_data(self):
        self.hide()
        self.LocationPage = LocationPage(parent=self)
        self.LocationPage.show()

    def segmentation_data(self):
        self.hide()
        self.SegmentationPage=SegmentationPage(parent=self)
        self.SegmentationPage.show()

    # 使用线程执行文件clear_cache操作
    def clear_cache(self):
        self.clear_cache_thread = ClearCacheThread(self.path_dict)
        self.clear_cache_thread.signal_finished.connect(self.slot_clear_cache)
        self.clear_cache_thread.start()

    def slot_clear_cache(self):
        self.init_table(message='缓存已清除')

    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

    def batch_visualize_data(self):
        checked_files_with_rows = self.table_files.get_checked_files_with_rows()
        # 当没有文件被选中时
        if not checked_files_with_rows:
            reply = QMessageBox.question(self, '批量可视化', '没有选中的文件. 是否要进行批量可视化?', QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.No:
                return
            filenames_to_visualize = {os.path.splitext(f)[0] for f in os.listdir(self.path_raw)}

        else:
            filenames_to_visualize = [filename for filename, _ in checked_files_with_rows]
        # 让用户选择一个文件夹来存储可视化结果
        chosen_directory = QFileDialog.getExistingDirectory(self, "选择文件夹存储结果", get_parent_directory(levels_up=3))
        if not chosen_directory:
            QMessageBox.information(self, '提示', '没有选择文件夹，操作已取消')
            print('没有选择文件夹，操作已取消')
            return
        current_datetime = datetime.now().strftime('%Y_%m%d_%H%M%S')
        new_folder_name = f'CalibratedData_{current_datetime}' + '_visualize'
        path_visualize = os.path.join(chosen_directory, new_folder_name)
        os.makedirs(path_visualize, exist_ok=True)  # 创建新文件夹
        self.thread = BatchVisualizeThread(filenames_to_visualize, path_visualize, path_source=self.path_raw,
                                           mainwindow=self)
        self.thread.start()

    def on_visualization_completed(self):
        self.label_info.setText(f'选中的文件已被批量可视化')

    def output_files(self):
        self.disable_buttons()
        checked_files_with_rows = self.table_files.get_checked_files_with_rows()
        files_to_output = [filename for filename, _ in checked_files_with_rows]
        if len(files_to_output) == 0:
            reply = QMessageBox.question(self, '批量导出', '没有选中的文件. 是否要进行批量导出?', QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.No:
                self.enable_buttons()
                return
            files_to_output = {os.path.splitext(f)[0] for f in os.listdir(self.path_raw)}
        files_to_output_ann = {os.path.splitext(f)[0] + '.ann' for f in files_to_output}
        # 检查每个文件是否有对应的标注文件
        for file_name in files_to_output_ann:
            corresponding_annotation = os.path.join(self.path_annotation, file_name)
            if not os.path.exists(corresponding_annotation):
                warning_message = QMessageBox(self)
                warning_message.setIcon(QMessageBox.Warning)
                warning_message.setText(f"文件 {file_name} 没有对应的标注文件，无法导出。")
                warning_message.setWindowTitle("警告")
                warning_message.setStandardButtons(QMessageBox.Ok)
                warning_message.exec_()
                return
        destination_dir = QFileDialog.getExistingDirectory(self, '选择存储文件夹', get_parent_directory(levels_up=3))
        if not destination_dir:
            self.enable_buttons()
            return  # 用户取消了选择

        current_datetime = datetime.now().strftime('%y%m%d%H%M')
        new_folder_name = f'LabelSIG_{current_datetime}_data'
        new_folder_path = os.path.join(destination_dir, new_folder_name)
        os.makedirs(new_folder_path, exist_ok=True)  # 创建新文件夹

        # 创建raw和annotation子文件夹
        raw_folder_path = os.path.join(new_folder_path, 'raw')
        annotation_folder_path = os.path.join(new_folder_path, 'annotation')
        os.makedirs(raw_folder_path, exist_ok=True)
        os.makedirs(annotation_folder_path, exist_ok=True)
        processing_times = []  # 记录每个文件的处理时间
        total_files = len(files_to_output)
        bar_length = 50
        for idx, file_name in enumerate(files_to_output):
            file_start_time = time.time()
            src_file_raw = os.path.join(self.path_raw, file_name + '.cfg')
            dst_file_raw = os.path.join(raw_folder_path, file_name + '.cfg')
            shutil.copy(src_file_raw, dst_file_raw)  # 复制数据文件到raw子文件夹
            src_file_raw = os.path.join(self.path_raw, file_name + '.dat')
            dst_file_raw = os.path.join(raw_folder_path, file_name + '.dat')
            shutil.copy(src_file_raw, dst_file_raw)  # 复制数据文件到raw子文件夹
            # 复制标注文件到annotation子文件夹
            file_name_ann = os.path.splitext(file_name)[0] + '.ann'
            src_file_annotation = os.path.join(self.path_annotation, file_name_ann)
            dst_file_annotation = os.path.join(annotation_folder_path, file_name_ann)
            shutil.copy(src_file_annotation, dst_file_annotation)
            file_end_time = time.time()
            processing_times.append(file_end_time - file_start_time)
            if self.label_info is not None:
                max_time_per_file = max(processing_times)
                # 这里我们考虑最大处理时间来预估剩余时间
                estimated_remaining_time = max_time_per_file * (total_files - idx - 1)
                progress_ratio = (idx + 1) / total_files
                filled_length = int(bar_length * progress_ratio)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                mins, secs = divmod(estimated_remaining_time, 60)
                self.label_info.setText(
                    f"[{bar}] ({idx + 1}/{total_files}) \n正在处理文件: {file_name} \n预计剩余等待时间: {int(mins)}分{int(secs)}秒")
        self.label_info.setText(f'文件已输出到 {new_folder_path}')  # 显示文件输出信息
        self.enable_buttons()

    def reconfigure_table_files(self):
        pos = self.table_files.pos()
        size = self.table_files.size()
        self.table_files.setParent(None)
        self.table_files = CustomTableWidget(self, self)
        self.table_files.move(pos)
        self.table_files.resize(size)

    def load_folder(self):

        script_dir = os.path.dirname(__file__)
        relative_path = '../../../'
        initial_path = os.path.abspath(os.path.join(script_dir, relative_path))
        fname = QFileDialog.getExistingDirectory(self, 'Open file', initial_path)
        print(fname)
        if fname:
            self.label_info.setText(f'文件夹 {fname} 正在加载')
            self.disable_buttons()
            self.load_thread = LoadFolderThread(mainwindow=self, path_dict=self.path_dict, path_source=fname)
            self.load_thread.signal_finished.connect(self.on_load_folder_finished)
            self.load_thread.start()

    def on_load_folder_finished(self, fname, dict_info):
        self.display_files_in_table(dict_info)
        self.enable_buttons()

    def display_files_in_table(self, dict_info):
        self.table_files.populate_table_from_dict(dict_info)

    def delete_checked_files(self):
        checked_files_with_rows = self.table_files.get_checked_files_with_rows()

        if not checked_files_with_rows:
            QMessageBox.information(self, "Info", "没有选中的文件.")
            return
        # 提取文件名用于确认删除操作
        filenames_to_delete = [filename for filename, _ in checked_files_with_rows]
        msg_content = "\n".join(filenames_to_delete)
        reply = QMessageBox.question(self, 'Confirm Delete',
                                     f"确定要删除以下文件吗?\n{msg_content}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 从后往前删除，这样不会因为删除前面的行而影响后面行的索引
            for _, row in reversed(checked_files_with_rows):
                self.table_files.delete_row(row)
            self.label_info.setText(f'选中的文件已被删除')


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    login = MainWindow()
    login.show()
    sys.exit(app.exec_())
